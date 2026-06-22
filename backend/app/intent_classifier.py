"""
LLM-based session intent classifier for Property Doors.

Sends the full session payload (transcript + metadata) to Google Gemini
and returns one of three classifications:
  - "high_intent"  -> strong buying signal, store lead
  - "mid_intent"   -> moderate interest, store lead
  - "no_intent"    -> casual / informational, discard

A deterministic rule-based pre-classifier runs FIRST so that obvious signals
are caught reliably without depending on the LLM's judgement.
"""
import json
import logging
import os
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

LLM_MODEL = os.getenv("LLM_MODEL", "gemini-2.5-flash-lite")

# -- High-intent trigger phrases (deterministic, checked before LLM) -----------
# Criteria:
#  1. Wants a site visit
#  2. Wants a callback from sales
#  3. Asks about the booking process
#  4. Asks about availability of units
#  5. Discusses budget
#  6. Discusses financing / home loan

HIGH_INTENT_TRIGGERS = [
    # 1. Site visit
    "site visit", "visit the site", "visit the property", "visit the flat",
    "schedule a visit", "schedule visit", "book a visit", "book visit",
    "can i visit", "want to visit", "plan a visit", "arrange a visit",
    "show me the property", "show me the flat", "show me the apartment",

    # 2. Callback / sales contact
    "call me", "callback", "call back", "contact me", "reach me",
    "give me a call", "have someone call", "talk to sales", "speak to sales",
    "talk to an agent", "speak to an agent", "sales team", "sales person",
    "my number", "my phone", "my contact", "reach out to me",
    "i will share my number", "i can share my number",

    # 3. Booking process
    "how to book", "how do i book", "booking process", "process of booking",
    "booking amount", "token amount", "booking fee", "registration charges",
    "advance payment", "booking formalities", "what is the booking",
    "how can i book", "want to book", "ready to book", "book it", "book now",
    "finalize", "lock in", "block the flat", "block the unit",

    # 4. Availability of units
    "available units", "unit availability", "is it available", "any units available",
    "available flats", "available apartments", "available villas",
    "how many units", "units left", "flats left", "inventory available",
    "do you have any", "is there any availability", "check availability",
    "still available", "what is available", "show available",

    # 5. Budget discussion
    "my budget", "budget is", "budget range", "i can afford", "my price range",
    "price range", "how much does it cost", "total cost", "all-in cost",
    "cost of the flat", "cost of the property", "negotiable", "can you negotiate",
    "any discount", "best price", "final price", "what is the price",
    "what will be the cost",

    # 6. Financing / home loan
    "home loan", "home loan eligibility", "bank loan", "loan approval",
    "loan eligibility", "emi", "emi calculation", "calculate emi",
    "finance", "financing", "mortgage", "down payment", "down-payment",
    "loan amount", "loan tenure", "interest rate", "bank financing",
    "hdfc", "sbi loan", "icici loan", "can i get a loan", "loan process",
    "pre-approved", "pre approved loan",
]

# -- No-intent trigger phrases (deterministic, checked before LLM) -------------
NO_INTENT_TRIGGERS = [
    "what is property doors", "what is propertybrix", "who are you",
    "what do you do", "tell me about yourself",
]

# -- Strict system prompt ------------------------------------------------------
SYSTEM_PROMPT = """You are a Real Estate Lead Scoring AI for Property Doors (India).
Analyse the session data below and classify the user's purchase intent.

OUTPUT RULES - CRITICAL:
- Respond with ONLY valid JSON. No markdown, no explanation, no extra text.
- Schema: {"classification": "<VALUE>", "reason": "<one sentence, max 200 chars>"}
- "classification" MUST be exactly one of: "high_intent", "mid_intent", "no_intent"

HIGH INTENT - classify as "high_intent" if ANY ONE of the following is true:

1. SITE VISIT - User asks for / wants to visit the property.
2. CALLBACK FROM SALES - User asks to be called or to speak with a sales agent.
3. BOOKING PROCESS - User asks how to book, what the booking amount is, or any formality related to purchasing.
4. UNIT AVAILABILITY - User asks whether any units / flats are available.
5. BUDGET DISCUSSION - User explicitly discusses their budget or asks about cost/price.
6. FINANCING / HOME LOAN - User asks about a home loan, EMI, down payment, or financing.

MID INTENT - classify as "mid_intent" if:
- User searched for properties, compared options, or asked 2+ specific questions
  about property details, prices, or locations BUT showed none of the 6 high-intent signals.
- OR user completed 3 of the 4 funnel steps (purpose, city, type, budget).

NO INTENT - classify as "no_intent" if:
- User only greeted (hi, hello, thanks), asked 1 generic FAQ (what is RERA?),
  OR had fewer than 2 meaningful exchanges with no buying signals.

EXAMPLES:
Input: "Can I schedule a site visit this week?"
Output: {"classification": "high_intent", "reason": "User requested a site visit - direct purchase action signal."}

Input: User searched for properties in Bangalore, asked about price ranges, compared 2BHK vs 3BHK
Output: {"classification": "mid_intent", "reason": "User explored and compared properties but showed no direct purchase action signal."}

Input: User only said "Hi" or "Hello"
Output: {"classification": "no_intent", "reason": "User only greeted the bot with no property search or buying signals."}
"""


def _build_prompt(session_data: Dict[str, Any]) -> str:
    history = session_data.get("chat_history", [])
    pages   = session_data.get("pages_visited", [])
    props_viewed  = session_data.get("properties_viewed", 0)
    time_spent    = session_data.get("time_spent_seconds", 0)
    questions     = session_data.get("questions_asked", [])

    history_str = "\n".join(
        f"[{m.get('role','?').upper()}] {m.get('content', m.get('message',''))}"
        for m in history
    )

    return f"""Session Data:
Time on site: {time_spent} seconds ({round(time_spent/60, 1)} minutes)
Pages visited: {", ".join(pages) if pages else "homepage only"}
Properties viewed: {props_viewed}
Questions asked: {json.dumps(questions) if questions else "none"}

Conversation Transcript:
{history_str or "(empty)"}

Classify the user's intent now. Respond with JSON only."""


def _rule_based_classify(session_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Deterministic pre-classifier. Runs BEFORE the LLM.
    Scans every user message in the transcript for trigger keywords.
    Returns a result dict immediately if a clear signal is found, else None.
    """
    history = session_data.get("chat_history", [])
    msg_count = len(history)

    # Collect all user text in lowercase for matching
    all_user_text = " ".join(
        m.get("content", m.get("message", "")).lower()
        for m in history if m.get("role") == "user"
    )

    # -- Hard high_intent signals (checked BEFORE message count gate) -----------
    for trigger in HIGH_INTENT_TRIGGERS:
        if trigger in all_user_text:
            reason = f"User message contained '{trigger}' - strong buying/urgency signal detected."
            logger.info(f"[Classifier] Pre-classifier -> high_intent (trigger: '{trigger}')")
            return {"classification": "high_intent", "reason": reason}

    # -- Hard no_intent: fewer than 3 messages total (just a greeting) ---------
    if msg_count < 3:
        logger.info(f"[Classifier] Pre-classifier -> no_intent (only {msg_count} messages, no urgency signals)")
        return {
            "classification": "no_intent",
            "reason": f"Session had only {msg_count} messages with no property search or buying signals."
        }

    # -- Hard no_intent: only generic info questions ---------------------------
    for trigger in NO_INTENT_TRIGGERS:
        if trigger in all_user_text and msg_count <= 4:
            logger.info(f"[Classifier] Pre-classifier -> no_intent (generic FAQ only: '{trigger}')")
            return {
                "classification": "no_intent",
                "reason": "User only asked generic informational questions with no buying intent."
            }

    return None  # Fall through to Gemini LLM


async def classify_user_intent(session_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Classifies a session's purchase intent using Gemini LLM.
    1. Runs deterministic pre-classifier first (fast, reliable).
    2. Falls back to Gemini LLM for ambiguous cases.

    Returns dict with keys:
      - classification: "high_intent" | "mid_intent" | "no_intent"
      - reason: str
    Returns None if the LLM call fails entirely.
    """
    from .llm_client import gemini_generate

    # -- Step 1: deterministic pre-check ---------------------------------------
    pre_result = _rule_based_classify(session_data)
    if pre_result:
        return pre_result

    # -- Step 2: Gemini LLM for ambiguous cases --------------------------------
    prompt = _build_prompt(session_data)
    logger.debug(f"[Classifier] Sending prompt ({len(prompt)} chars) to Gemini")

    full_prompt = (
        SYSTEM_PROMPT + "\n\n" + prompt +
        '\n\nRespond with ONLY valid JSON. No markdown. Format: '
        '{"classification": "<high_intent|mid_intent|no_intent>", "reason": "<one sentence max 200 chars>"}'
    )

    raw = ""
    try:
        raw = await gemini_generate(full_prompt, max_tokens=120, temperature=0.0)

        if not raw:
            raise ValueError("Gemini returned empty response")

        # Strip markdown code fences if Gemini wraps in ```json ... ```
        raw = raw.strip()
        if raw.startswith("```"):
            parts = raw.split("```")
            raw = parts[1] if len(parts) > 1 else raw
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        result = json.loads(raw)
        classification = result.get("classification", "").lower().strip()
        reason         = result.get("reason", "No reason provided.")

        if classification not in ("high_intent", "mid_intent", "no_intent"):
            logger.warning(f"[Classifier] Unexpected value: '{classification}' - defaulting to no_intent")
            classification = "no_intent"

        logger.info(f"[Classifier] Gemini result: {classification} | Reason: {reason}")
        return {"classification": classification, "reason": reason}

    except json.JSONDecodeError as e:
        logger.error(f"[Classifier] Failed to parse Gemini JSON: {e} | raw={raw[:200]}")
        # Safety fallback: sessions with enough messages get mid_intent
        msg_count = len(session_data.get("chat_history", []))
        if msg_count >= 4:
            return {
                "classification": "mid_intent",
                "reason": "LLM parse failed; session had sufficient engagement to qualify as mid-intent."
            }
        return None

    except Exception as e:
        logger.error(f"[Classifier] Gemini call failed: {e}")
        return None
