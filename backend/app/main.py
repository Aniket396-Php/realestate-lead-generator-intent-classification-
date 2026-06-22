"""
FastAPI main application - Property Doors AI Chatbot v2.
Fixes: clean routing, funnel advance, FAQ/Nav prefix, response safety, logging.
"""

import json
import logging
import os
import re
import sys
from typing import Any, Dict, Optional

# Fix: ensure stdout/stderr can handle emoji/unicode on Windows (cp1252 fix)
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass

import asyncio
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .models import ChatRequest, EnquiryRequest, UserProfile
from .intent import classify_intent
from .property_search import search_properties_from_json, get_all_locations, _match_reason
from .faq_rag import answer_faq, get_faq_options
from .navigation import get_navigation, get_nav_options
from .storage import append_interaction, save_enquiry, save_hot_lead
from .intent_classifier import classify_user_intent
from .llm_client import gemini_generate
from .state import (get_session, add_message_to_history,
                    get_missing_sales_criteria, generate_sales_prompt,
                    get_sessions_to_classify, mark_session_classified,
                    update_session_activity)
from .supabase_service import log_message, get_properties, log_user_activity

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger(__name__)

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "data", "config.json")

def load_config() -> Dict:
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception:
        return {}

CONFIG  = load_config()
COMPANY = CONFIG.get("company_name", "Property Doors")
PHONE   = CONFIG.get("phone", "our support team")
EMAIL   = CONFIG.get("email", "")

app = FastAPI(title="Property Doors AI Chatbot API", version="2.0.0",
              docs_url="/docs", redoc_url="/redoc")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

BASE_DIR     = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
WIDGET_FILE  = os.path.join(FRONTEND_DIR, "chatbot-embed.js")
DEMO_FILE    = os.path.join(FRONTEND_DIR, "demo.html")


@app.on_event("startup")
async def startup_event():
    logger.info(f"Property Doors Chatbot v2 — {COMPANY} — Ready ✅")
    # Start the idle intent classification worker
    asyncio.create_task(intent_classification_worker())


async def intent_classification_worker():
    """
    Background worker: every 30 s, checks for sessions idle ≥ 60 s.
    Delegates to lead_pipeline.run_classification_pipeline() which handles:
      - < 1 min threshold → discard
      - LLM classification → high_intent / mid_intent / no_intent
      - Supabase storage for qualifying leads
    """
    from .lead_pipeline import run_classification_pipeline
    logger.info("Intent classification worker started.")

    while True:
        try:
            await asyncio.sleep(30)   # poll every 30 seconds
            to_classify = get_sessions_to_classify(idle_seconds=60)  # 1 min idle

            for session_id, session in to_classify:
                try:
                    outcome = await run_classification_pipeline(session_id, session)
                    logger.info(f"[Worker] [{session_id}] Pipeline outcome: {outcome.upper()}")
                    # Mark classified AFTER successful pipeline — prevents re-processing
                    mark_session_classified(session_id)
                except Exception as e:
                    logger.error(f"[Worker] [{session_id}] Pipeline threw an exception: {e}", exc_info=True)
                    # Do NOT mark classified so it can be retried next cycle

        except Exception as e:
            logger.error(f"[Worker] Unexpected error in classification loop: {e}", exc_info=True)




# ── Frontend Serving ───────────────────────────────────────────────────────────

# Serve specific frontend entries
@app.get("/", include_in_schema=False)
async def root():
    return FileResponse(DEMO_FILE)

@app.get("/widget.js", include_in_schema=False)
async def widget_js():
    return FileResponse(WIDGET_FILE, media_type="application/javascript; charset=utf-8",
                        headers={"Cache-Control": "no-store, max-age=0"})

@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "ok", "service": "propertybrix-chatbot-api",
            "version": "2.0.0", "company": COMPANY}


# ── Funnel helpers ─────────────────────────────────────────────────────────────

def _funnel_options(missing: str) -> list:
    """Return clickable button options for the next missing funnel field."""
    if missing == "purpose":
        return [
            {"label": "Buy Property",  "msg": "Buy Property"},
            {"label": "Rent Property", "msg": "Rent Property"},
            {"label": "New Projects",  "msg": "New Projects"},
        ]
    if missing == "location":
        return get_all_locations(limit=5)

    if missing == "property_type":
        return [
            {"label": "1 BHK",      "msg": "1 BHK"},
            {"label": "2 BHK",      "msg": "2 BHK"},
            {"label": "3 BHK",      "msg": "3 BHK"},
            {"label": "Villa",      "msg": "Villa"},
            {"label": "Plot",       "msg": "Plot"},
            {"label": "Office",     "msg": "Office"},
            {"label": "Commercial", "msg": "Commercial"},
            {"label": "Penthouse",  "msg": "Penthouse"},
        ]
    if missing == "budget":
        return [
            {"label": "Rs. 30L - 50L", "msg": "BUDGET:30L-50L"},
            {"label": "Rs. 50L - 80L", "msg": "BUDGET:50L-80L"},
            {"label": "Rs. 80L - 1Cr", "msg": "BUDGET:80L-1Cr"},
            {"label": "Rs. 1Cr+",        "msg": "BUDGET:1Cr+"},
        ]
    return []


async def _run_funnel(session: dict, session_id: str) -> Dict[str, Any]:
    """
    Check what funnel field is still missing.
    - If something missing: return the prompt + options for it.
    - If all collected: run property search, reset session.
    FIX (Bug 19): Answer is saved BEFORE this is called, so
    get_missing_sales_criteria always reflects the updated state.
    """
    missing = get_missing_sales_criteria(session_id)
    if missing:
        return {
            "type": "text_response",
            "message": generate_sales_prompt(missing, session["collected_data"]),
            "options": _funnel_options(missing),
        }

    # All 4 criteria collected — run search
    # Query Supabase instead of local JSON
    c = session["collected_data"]
    
    # Parse budget string (e.g., "30L to 50L") to numeric values for DB query
    # Database stores price as decimals of Crores (0.35 = 35 Lakhs, 1.2 = 1.2 Cr)
    min_p, max_p = 0.0, 999.0
    budget_str = c.get('budget', '')
    
    try:
        if ' to ' in budget_str:
            parts = budget_str.replace('₹', '').replace('L', '').split(' to ')
            # Handle min
            min_p = float(parts[0].strip()) / 100.0 # 30L -> 0.30
            # Handle max
            if 'Cr' in parts[1]:
                max_p = float(parts[1].replace('Cr', '').strip())
            else:
                max_p = float(parts[1].strip()) / 100.0 # 50L -> 0.50
        elif 'above' in budget_str:
            val = budget_str.replace('above ', '').replace('₹', '').replace('Cr', '').strip()
            min_p = float(val)
            max_p = 999.0
    except Exception as e:
        logger.warning(f"Budget parse error for '{budget_str}': {e}")

    # Parse Property Type (BHK vs Villa etc.)
    p_choice = c.get('property_type', '').lower()
    query_ptype = None
    query_bedrooms = None
    
    if 'bhk' in p_choice:
        try: 
            # Parse '2 BHK' etc.
            match = re.search(r'(\d+)', p_choice)
            if match:
                query_bedrooms = int(match.group(1))
        except: pass
        query_ptype = 'apartment'
    elif 'apartment' in p_choice or 'flat' in p_choice:
        query_ptype = 'apartment'
    elif 'villa' in p_choice:
        query_ptype = 'villa'
    elif 'commercial' in p_choice:
        query_ptype = 'commercial'
    elif 'plot' in p_choice:
        query_ptype = 'plot'
    elif 'office' in p_choice:
        query_ptype = 'office'
    elif 'penthouse' in p_choice:
        query_ptype = 'penthouse'

    logger.info(f"[{session_id}] Search Criteria: city={c.get('location')}, ptype={query_ptype}, bedrooms={query_bedrooms}, price={min_p}-{max_p}")

    print(f"\n--- DEBUG SEARCH ---\nSession: {session_id}\nCriteria: city={c.get('location')}, ptype={query_ptype}, bedrooms={query_bedrooms}, price={min_p}-{max_p}, purpose={c.get('purpose')}")
    
    db_results = get_properties(
        city=c.get('location'),
        ptype=query_ptype,
        bedrooms=query_bedrooms,
        min_price=min_p,
        max_price=max_p,
        purpose=c.get('purpose')
    )
    
    print(f"Results count: {len(db_results) if db_results else 0}\n--------------------\n")

    
    # Transform database results to UI format
    results = []
    for i, p in enumerate(db_results):
        results.append({
            "id": str(p.get("id", f"PB-{i}")),
            "title": p.get("title", "Property Listing"),
            "price": p.get("price_label", f"Rs. {p.get('price')}"),
            "location": p.get("location", p.get("city", "India")),
            "bedrooms": p.get("bedrooms"),
            "bathrooms": p.get("bathrooms"),
            "area_sqft": p.get("area_sqft"),
            "status": p.get("status"),
            "amenities": p.get("amenities"),
            "url": p.get("url", "https://propertybrix.com"),
            "reason": _match_reason(p, c)
        })

    session["collected_data"] = {}
    session["current_flow"]   = None
    
    return {
        "type": "property_results",
        "message": f"I found {len(results)} properties matching your search:",
        "results": results
    }


# ── Background Lead Scoring ───────────────────────────────────────────────────

# (process_intent_lead removed, replaced by background worker)


# ── Main chat endpoint ─────────────────────────────────────────────────────────

@app.post("/chat", tags=["Chat"])
async def chat(request: ChatRequest, background_tasks: BackgroundTasks) -> Dict[str, Any]:
    session_id = request.session_id
    user       = request.user
    message    = (request.message or "").strip()

    if not user:
        user = UserProfile(
            id=f"guest_{session_id}",
            email=f"guest_{session_id}@propertybrix.local",
            name="Guest",
            phone="N/A"
        )

    # --- Clean display message for logs (strip internal prefixes) ---
    display_msg = message
    for pfx in ("FAQ_QUERY:", "NAV_QUERY:", "BUDGET:"):
        if message.startswith(pfx):
            display_msg = message[len(pfx):]
            break

    logger.info(f"[{session_id}] ({user.email}): {display_msg[:100]}")
    add_message_to_history(session_id, "user", display_msg)  # Bug 17 fix: log clean msg

    response: Optional[Dict[str, Any]] = None
    intent = "GENERAL"

    try:
        # Store user info for delayed classification (3 mins later)
        session = get_session(session_id, user_info=user.dict())

        # ══════════════════════════════════════════════════════════════
        # ROUTING — explicit prefixes (highest priority, no ambiguity)
        # ══════════════════════════════════════════════════════════════

        if message.startswith("FAQ_QUERY:"):          # Bug 1 fix
            question = message[len("FAQ_QUERY:"):]
            intent   = "FAQ"
            response = await answer_faq(question)

        elif message.startswith("NAV_QUERY:"):         # Bug 2 fix
            dest     = message[len("NAV_QUERY:"):]
            intent   = "NAVIGATION"
            response = await get_navigation(dest)

        elif message.startswith("BUDGET:"):            # Bug 7 fix: structured budget
            code = message[len("BUDGET:"):]
            budget_map = {
                "30L-50L": "30L to 50L",
                "50L-80L": "50L to 80L",
                "80L-1Cr": "80L to 1Cr",
                "1Cr+":    "above 1Cr",
            }
            session["collected_data"]["budget"] = budget_map.get(code, code)
            intent   = "PROPERTY_SEARCH"
            response = await _run_funnel(session, session_id)

        # ── Hard menu triggers ──────────────────────────────────────

        elif message == "MENU_FIND_PROPERTIES":
            session["collected_data"] = {}
            session["current_flow"]   = "PROPERTY_SEARCH"
            intent   = "PROPERTY_SEARCH"
            response = await _run_funnel(session, session_id)

        elif message == "MENU_ASK_FAQ":
            session["current_flow"]   = None
            session["collected_data"] = {}
            intent   = "FAQ"
            response = {
                "type": "text_response",
                "message": "Here are some commonly asked questions! Tap one for an instant answer.",
                "options": get_faq_options(),
            }

        elif message == "MENU_NAVIGATE":
            session["current_flow"]   = None
            session["collected_data"] = {}
            intent   = "NAVIGATION"
            response = {
                "type": "text_response",
                "message": "Here are some quick links to navigate around Property Doors:",
                "options": get_nav_options(),
            }

        elif message == "OTHER_LOCATION":             # Dynamic city list
            intent   = "PROPERTY_SEARCH"
            response = {
                "type": "text_response",
                "message": "Here are all the cities currently in our inventory. Tap one to search:",
                "options": get_all_locations(limit=None),
            }


        # ── Active property search funnel ───────────────────────────

        elif session.get("current_flow") == "PROPERTY_SEARCH":
            # Funnel escape: short/stop words should exit the funnel, not be
            # stored as a property type / location / budget answer.
            _FUNNEL_EXITS = {
                "wait", "stop", "cancel", "exit", "quit", "back", "no",
                "nope", "nah", "nevermind", "never mind", "not now",
                "skip", "reset", "restart", "start over", "main menu",
            }
            if message.lower().strip() in _FUNNEL_EXITS:
                session["collected_data"] = {}
                session["current_flow"]   = None
                intent   = "GENERAL"
                # Let the LLM give a natural reply
                llm_response = await gemini_generate(
                    f"You are a helpful assistant for {COMPANY}, a real estate platform in India. "
                    f"The user just said: \"{message}\". "
                    "They seem to have paused or cancelled a property search. "
                    "Acknowledge briefly and let them know you can help search properties, "
                    "answer FAQs, or navigate the site. Keep it to 2 sentences.",
                    max_tokens=80, temperature=0.6
                )
                response = {"type": "text_response", "message": llm_response or (
                    f"No problem! 😊 Whenever you're ready, I can help you search properties, "
                    f"answer questions, or navigate {COMPANY}."
                )}
            else:
                # Bug 19 fix: SAVE user's answer FIRST, THEN compute next step
                missing_now = get_missing_sales_criteria(session_id)
                if missing_now:
                    session["collected_data"][missing_now] = message
                intent   = "PROPERTY_SEARCH"
                response = await _run_funnel(session, session_id)

        # ── Free-text: classify intent ──────────────────────────────

        else:
            intent = await classify_intent(message)
            logger.info(f"[{session_id}] Classified: {intent}")

            if intent == "PROPERTY_SEARCH":
                session["collected_data"] = {}
                session["current_flow"]   = "PROPERTY_SEARCH"
                response = await _run_funnel(session, session_id)

            elif intent == "FAQ":
                response = await answer_faq(message)

            elif intent == "NAVIGATION":
                response = await get_navigation(message)

            elif intent == "GREETING":
                response = {"type": "text_response", "message": (
                    f"👋 Hello {user.name}! Welcome to {COMPANY}.\n\n"
                    "I can help you find properties, answer questions, or navigate the site.\n"
                    "What can I help you with today? 🏠"
                )}

            elif intent == "GRATITUDE":
                response = {"type": "text_response", "message": (
                    "You're welcome! 😊\n\nIs there anything else I can help you with?"
                )}

            elif intent == "GENERAL":
                # Use Google Gemini to give a customized, context-aware reply
                prompt = (
                    f"You are a helpful, friendly AI assistant for {COMPANY}, a leading real estate platform in India.\n"
                    f"Our features include:\n"
                    f"- Searching properties (by city like Mumbai, Pune, Bangalore; by BHK like 1BHK, 2BHK; by budget)\n"
                    f"- Answering FAQs (home loans, RERA, registration, booking fees, documents)\n"
                    f"- Helping navigate pages on the website\n\n"
                    f"User said: \"{message}\"\n\n"
                    f"Respond directly and helpfully in 2-3 sentences, keeping the context of {COMPANY} real estate. "
                    f"If they seem to be looking for properties, invite them to use the property search feature. "
                    f"Be warm, conversational, and never robotic."
                )
                llm_response = await gemini_generate(prompt, max_tokens=150, temperature=0.6)

                if not llm_response:
                    llm_response = (
                        f"👋 Hi! I'm your {COMPANY} assistant. I can help you search properties (in Mumbai, Pune, Bangalore, etc.), "
                        "answer loan & registration FAQs, or guide you to any page on our site.\n\n"
                        f"What are you looking for today? Feel free to ask, or contact us at 📞 {PHONE}!"
                    )

                response = {"type": "text_response", "message": llm_response}

            else:
                response = {"type": "text_response", "message": (
                    f"I'm your {COMPANY} assistant. I can help you:\n"
                    "• Search properties by city, type & budget\n"
                    "• Answer questions about loans, RERA & charges\n"
                    "• Navigate to any page on the site\n\n"
                    f"Feel free to ask! Or call us at 📞 {PHONE}"
                )}

        # Bug 16 fix: guarantee response is always a valid dict
        if response is None:
            response = {"type": "text_response",
                        "message": "Sorry, I couldn't process that. Please try again."}

        # ── Log interaction ──────────────────────────────────────────
        final_text = response.get("message", "")
        add_message_to_history(session_id, "bot", final_text)
        
        # 🟢 Supabase logging
        log_message(user.id, session_id, "user", display_msg)
        log_message(user.id, session_id, "bot", final_text)

        background_tasks.add_task(
            append_interaction,
            user_id=user.id, email=user.email,
            message=display_msg,
            intent=intent, response=final_text, session_id=session_id
        )
        # (Immediate classification task removed)


        return response

    except Exception as e:
        logger.error(f"[{session_id}] Error: {e}", exc_info=True)
        raise HTTPException(status_code=500,
                            detail="An unexpected error occurred. Please try again.")


@app.post("/track-activity", tags=["Leads"])
async def track_activity(request: Dict[str, Any]):
    user_id = request.get("user_id")
    if not user_id:
        return {"status": "ignored"}
    
    log_user_activity(
        user_id=user_id,
        pages=request.get("pages", []),
        properties_viewed=request.get("property_count", 0),
        time_spent=request.get("time_spent", "0s")
    )
    
    # Sync activity to session for background classification
    sid = request.get("session_id")
    if sid:
        update_session_activity(
            session_id=sid,
            pages=request.get("pages", []),
            properties_viewed=request.get("property_count", 0)
        )
        
    return {"status": "success"}


@app.post("/enquire", tags=["Leads"])
async def submit_enquiry(request: EnquiryRequest, background_tasks: BackgroundTasks):
    user = request.user
    if not user:
        raise HTTPException(status_code=401, detail="User must be logged in.")

    enquiry = save_enquiry(
        user_id=user.id, email=user.email,
        name=user.name or "Guest", phone=user.phone or "Unknown",
        property_id=request.property_id, message=request.message
    )
    if enquiry:
        logger.info(f"Enquiry {enquiry['enquiry_id']} for property {request.property_id}")
        return {"status": "success",
                "message": "Enquiry sent! The property owner will contact you shortly."}
    raise HTTPException(status_code=500, detail="Failed to save enquiry.")

# ── Static File Overlay (Catch-all) ──────────────────────────────────────────
# Mount at the end to avoid intercepting API routes (Bug 405 Fix)
app.mount("/", StaticFiles(directory=FRONTEND_DIR), name="static")

