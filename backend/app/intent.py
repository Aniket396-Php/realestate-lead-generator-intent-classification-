"""
Intent classifier for Property Doors chatbot.
Uses keyword matching first, then falls back to Google Gemini LLM.
Intents: PROPERTY_SEARCH, FAQ, NAVIGATION, GREETING, GRATITUDE, GENERAL
"""

import logging
import os
import re

from .llm_client import gemini_generate

logger = logging.getLogger(__name__)

# â”€â”€ Strict keyword sets (no overlap) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

# Navigation â€” must be checked FIRST (very specific phrases)
NAVIGATION_KEYWORDS = [
    "go to", "take me", "open page", "navigate", "show page",
    "properties page", "contact page", "about page", "home page",
    "login", "sign up", "sign in", "register", "create account",
    "post property", "list my property", "add listing", "sell property",
    "wishlist", "saved", "dashboard", "my account", "my profile",
    "blog", "faq page", "emi calculator", "loan calculator",
    "redirect", "goto",
]

# FAQ â€” questions about process, charges, services (specific phrases)
# NOTE: Avoid single common words like "how" — use FULL PHRASES only to prevent
# accidental FAQ routing of property search / general queries.
FAQ_KEYWORDS = [
    "home loan", "emi", "interest rate", "bank loan", "finance", "mortgage",
    "listing charges", "service fee", "brokerage", "commission", "agent fee",
    "rera", "rera registered", "legal document", "documents needed",
    "what is propertybrix", "what is property doors",
    "how does", "how do i", "how to search", "how to buy", "how to sell",
    "tell me about propertybrix", "explain rera",
    "registration process", "stamp duty", "agreement", "possession date",
    "site visit", "schedule visit", "inspection",
    "phone number", "contact support", "email support",
    "post property charges", "list property charges",
    "tier 2", "which cities", "locations available",
    "who are you", "about propertybrix", "about property doors",
    "what do you offer", "platform features",
    "how long does", "how much time", "process take",
]

# Property Search â€” specific real estate search terms
# IMPORTANT: Keep these SPECIFIC. Avoid vague phrases like "find property" or
# "best property" — those are general questions that should reach the LLM for
# a conversational reply, not be hard-routed to the funnel.
PROPERTY_KEYWORDS = [
    "bhk", "flat", "apartment", "villa", "plot", "penthouse", "studio",
    "commercial", "office space", "shop",
    "buy property", "purchase property", "invest in property",
    "properties for sale", "properties for rent", "show me properties",
    "show me flats", "show me apartments", "show me villas",
    "under ₹", "below ₹", "above ₹",
    "sqft", "sq ft", "bedroom", "bathroom",
    "ready to move", "under construction", "new launch",
    "search properties", "available properties",
    "2bhk", "3bhk", "1bhk", "4bhk",
    "in mumbai", "in pune", "in bangalore", "in hyderabad",
    "in delhi", "in ahmedabad", "in noida", "in chennai",
    "bandra", "wakad", "hinjewadi", "whitefield", "gachibowli",
    "dwarka", "sarjapur", "bkc", "jubilee hills",
    "lakh", "crore", "₹", "properties in",
]

GREETING_KEYWORDS = [
    "hi", "hello", "hey", "good morning", "good afternoon",
    "good evening", "namaste", "hola", "greetings",
    "hii", "helo", "sup", "what's up",
]

GRATITUDE_KEYWORDS = [
    "thanks", "thank you", "thank u", "thx", "ty",
    "ok thanks", "okay",  "got it", "noted", "perfect",
    "great", "awesome", "wonderful", "helpful",
    "that's all", "no more", "bye", "goodbye",
]


def _keyword_classify(message: str) -> str | None:
    msg = message.lower().strip()
    words = re.findall(r"\w+", msg)

    # Short greetings â€” check word by word
    if len(words) <= 4 and any(w in GREETING_KEYWORDS for w in words):
        return "GREETING"

    # Short gratitude â€” check word by word
    if len(words) <= 6 and any(
        phrase in msg for phrase in GRATITUDE_KEYWORDS
        if " " in phrase
    ) or (len(words) <= 4 and any(w in GRATITUDE_KEYWORDS for w in words)):
        return "GRATITUDE"

    # Navigation â€” check phrases first (highest priority)
    nav_score = sum(1 for kw in NAVIGATION_KEYWORDS if kw in msg)

    # FAQ â€” check specific phrases
    faq_score = sum(1 for kw in FAQ_KEYWORDS if kw in msg)

    # Property â€” check keywords
    prop_score = sum(1 for kw in PROPERTY_KEYWORDS if kw in msg)

    logger.debug(f"Scores â€” NAV:{nav_score} FAQ:{faq_score} PROP:{prop_score} for '{message[:50]}'")

    # Navigation wins if it has any match
    if nav_score > 0 and nav_score >= faq_score and nav_score >= prop_score:
        logger.info(f"Intent (keyword): NAVIGATION for: '{message[:60]}'")
        return "NAVIGATION"

    # FAQ wins if score is higher than property
    if faq_score > 0 and faq_score >= prop_score:
        logger.info(f"Intent (keyword): FAQ for: '{message[:60]}'")
        return "FAQ"

    # Property search
    if prop_score > 0:
        logger.info(f"Intent (keyword): PROPERTY_SEARCH for: '{message[:60]}'")
        return "PROPERTY_SEARCH"

    return None   # Fall through to LLM


async def _llm_classify(message: str) -> str:
    prompt = (
        "Classify this user message into ONE of these intents:\n"
        "PROPERTY_SEARCH, FAQ, NAVIGATION, GREETING, GRATITUDE, GENERAL\n\n"
        "Definitions:\n"
        "- PROPERTY_SEARCH: Searching for flat/villa/plot by location, price, type, BHK\n"
        "- FAQ: Questions about home loans, RERA, charges, documents, services, process\n"
        "- NAVIGATION: Wants to go to a specific page (contact, about, login, post property)\n"
        "- GREETING: Just saying hi/hello/namaste\n"
        "- GRATITUDE: Saying thanks/ok/bye/got it/great\n"
        "- GENERAL: Anything else not covered by the above\n\n"
        f"Message: \"{message}\"\n\n"
        "Reply with ONLY the intent word. No explanation."
    )
    result = await gemini_generate(prompt, max_tokens=10, temperature=0.0)
    if result:
        valid  = {"PROPERTY_SEARCH", "FAQ", "NAVIGATION", "GREETING", "GRATITUDE", "GENERAL"}
        intent = result.strip().upper()
        intent = intent if intent in valid else "GENERAL"
        logger.info(f"Intent (Gemini): {intent} for: '{message[:60]}'")
        return intent
    # Smart fallback if Gemini unavailable
    logger.warning(f"Gemini classify failed, using smart fallback for: '{message[:60]}'")
    return _smart_fallback(message)


def _smart_fallback(message: str) -> str:
    """Bug 14 fix: reuse keyword scoring instead of primitive word checks."""
    msg = message.lower()
    nav_score  = sum(1 for kw in NAVIGATION_KEYWORDS if kw in msg)
    faq_score  = sum(1 for kw in FAQ_KEYWORDS        if kw in msg)
    prop_score = sum(1 for kw in PROPERTY_KEYWORDS   if kw in msg)

    if nav_score  > 0 and nav_score  >= faq_score and nav_score >= prop_score:
        return "NAVIGATION"
    if faq_score  > 0 and faq_score  >= prop_score:
        return "FAQ"
    if prop_score > 0:
        return "PROPERTY_SEARCH"
    # Last-resort heuristics — check property intent BEFORE generic question words
    if any(w in msg for w in ["property", "flat", "house", "apartment", "buy", "rent", "get property", "best property"]):
        return "PROPERTY_SEARCH"
    if any(w in msg for w in ["what is", "how does", "how do i", "how to", "explain", "tell me about"]):
        return "FAQ"
    return "GENERAL"



async def classify_intent(message: str) -> str:
    keyword_result = _keyword_classify(message)
    if keyword_result:
        return keyword_result
    return await _llm_classify(message)

