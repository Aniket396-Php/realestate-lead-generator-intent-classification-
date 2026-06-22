"""
FAQ module for property doors chatbot.
Uses smart keyword matching on the config.json FAQ list — INSTANT, no LLM needed.
Only falls back to Google Gemini for genuinely complex questions not in the FAQ list.
"""

import json
import logging
import os
import re

from .llm_client import gemini_generate

logger = logging.getLogger(__name__)

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "data", "config.json")


def _load_config():
    with open(CONFIG_FILE, "r", encoding="utf-8-sig") as f:
        return json.load(f)

def get_faq_options() -> list:
    config = _load_config()
    faqs = config.get("faqs", [])
    options = []
    # Cap to top 6 FAQs so UI doesn't overload
    for faq in faqs[:6]:
        q = faq.get("question", "")
        if q:
            # We truncate label slightly if it's too long
            label = q if len(q) < 40 else q[:37] + "..."
            # Use FAQ_QUERY: prefix so the backend routes this DIRECTLY to FAQ,
            # bypassing intent classification entirely â€” 100% reliable.
            options.append({"label": f"â“ {label}", "msg": f"FAQ_QUERY:{q}"})
    return options


# â”€â”€ Keyword map for instant FAQ lookup â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Maps keywords â†’ FAQ index in config.json
FAQ_TRIGGER_MAP = {
    # About the company
    "what is property doors":  0,
    "what is propertybrix":   0,
    "about property doors":    0,
    "about propertybrix":     0,
    "who are you":            0,
    "tell me about":          0,

    # Search
    "how do i search":        1,
    "how to search":          1,
    "search properties":      1,
    "find property":          1,
    "filter":                 1,

    # Verified / trusted
    "verified":               2,
    "fake":                   2,
    "trust":                  2,
    "genuine":                2,
    "listings verified":      2,

    # Listing charges
    "listing charges":        3,
    "list my property":       3,
    "charges for listing":    3,
    "post property charges":  3,
    "how much to list":       3,
    "free listing":           3,
    "premium listing":        3,

    # Home loan
    "home loan":              4,
    "loan":                   4,
    "emi":                    4,
    "bank":                   4,
    "finance":                4,
    "mortgage":               4,
    "interest rate":          4,
    "pre-approved":           4,

    # Site visit
    "site visit":             5,
    "schedule visit":         5,
    "visit property":         5,
    "schedule":               5,
    "inspection":             5,

    # RERA
    "rera":                   6,
    "rera registered":        6,
    "regulatory":             6,

    # Selling
    "sell":                   7,
    "seller":                 7,
    "how do i sell":          7,
    "post my property":       7,

    # Cities
    "tier 2":                 8,
    "which cities":           8,
    "cities available":       8,
    "locations":              8,
    "where do you operate":   8,
    "nashik":                 8,
    "jaipur":                 8,
    "surat":                  8,

    # Registration
    "registration process":   9,
    "how long":               9,
    "how many days":          9,
    "registration time":      9,
    "time to register":       9,

    # Documents
    "documents":              10,
    "document":               10,
    "aadhaar":                10,
    "pan card":               10,
    "income proof":           10,
    "what do i need":         10,

    # Brokerage
    "brokerage":              11,
    "commission":             11,
    "service fee":            11,
    "agent fee":              11,
    "charges":                11,
    "how much do you charge": 11,
}


def _instant_faq_match(question: str, faqs: list) -> str | None:
    """Returns answer string instantly using keyword map. No LLM."""
    q = question.lower().strip()

    # 1. Try phrase match first (longer â†’ more specific)
    sorted_keys = sorted(FAQ_TRIGGER_MAP.keys(), key=len, reverse=True)
    for phrase in sorted_keys:
        if phrase in q:
            idx = FAQ_TRIGGER_MAP[phrase]
            if idx < len(faqs):
                logger.info(f"FAQ instant match: '{phrase}' â†’ FAQ[{idx}]")
                return faqs[idx]["answer"]

    # 2. Word overlap scoring as fallback
    best_answer, best_score = None, 0
    q_words = set(re.findall(r"\w+", q))
    for faq in faqs:
        faq_words = set(re.findall(r"\w+", faq["question"].lower()))
        overlap   = len(faq_words & q_words)
        tfidf_score = overlap / (len(faq_words) + 1)  # normalise
        if tfidf_score > best_score:
            best_score = tfidf_score
            best_answer = faq["answer"]

    if best_score > 0.35:  # raised threshold — prevents weak/vague matches from hitting FAQ
        logger.info(f"FAQ word-overlap match (score={best_score:.2f})")
        return best_answer

    return None


async def answer_faq(message: str):
    config  = _load_config()
    faqs    = config.get("faqs", [])
    company = config.get("company_name", "property doors")
    phone   = config.get("phone", "our support team")
    email   = config.get("email", "")
    hours   = config.get("working_hours", "")

    # â”€â”€ Instant lookup (no LLM) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    instant = _instant_faq_match(message, faqs)
    if instant:
        return {"type": "text_response", "message": instant}

    # ── Gemini LLM fallback (only if no instant match) ────────────────────────
    logger.info(f"FAQ: no instant match, trying Gemini for '{message[:60]}'")
    faq_context = "\n".join(
        f"Q: {f['question']}\nA: {f['answer']}" for f in faqs
    )
    prompt = (
        f"You are a helpful assistant for {company}, a real estate platform in India.\n"
        f"Contact: {phone} | {email} | Hours: {hours}\n\n"
        f"KNOWLEDGE BASE:\n{faq_context}\n\n"
        f"USER QUESTION: {message}\n\n"
        "Answer concisely using ONLY the knowledge base above. "
        "If not covered, say: 'Please contact us at "
        f"{phone} or {email} for accurate details.'\n\n"
        "ANSWER:"
    )
    answer = await gemini_generate(prompt, max_tokens=250, temperature=0.2)
    if answer:
        return {"type": "text_response", "message": answer}


    # â”€â”€ Final fallback â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    return {
        "type": "text_response",
        "message": (
            f"I don't have a specific answer for that in my knowledge base.\n\n"
            f"ðŸ“ž Call us: {phone}\n"
            f"ðŸ“§ Email: {email}\n"
            f"ðŸ• Hours: {hours}\n\n"
            f"Or browse our full FAQ at:\n"
            f"https://www.propertybrix.com/en-new/faq"
        ),
    }

