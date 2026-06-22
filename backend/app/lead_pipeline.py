"""
lead_pipeline.py — Intent-based lead classification, archiving, and storage.

Pipeline flow (called by the background worker in main.py):
  1. Check minimum time threshold (< 60 s → discard, no LLM call).
  2. Build structured session payload.
  3. Call LLM classifier.
  4. If no_intent → discard (nothing stored).
  5. If high_intent / mid_intent → store in conversations + correct lead table.

All storage uses the service-role Supabase admin client to bypass RLS.
"""

import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────
MIN_SESSION_SECONDS = 10   # discard sessions shorter than 10 seconds (lowered so urgency signals are caught even in short sessions)


# ── Helpers ────────────────────────────────────────────────────────────────────

def extract_questions(history: List[Dict]) -> List[str]:
    """
    Extract all user messages that look like questions (end with '?')
    from the conversation history.
    """
    questions = []
    for msg in history:
        if msg.get("role") == "user":
            content = msg.get("content", msg.get("message", "")).strip()
            if content.endswith("?"):
                questions.append(content)
    return list(dict.fromkeys(questions))   # deduplicate, preserve order


def get_session_duration(session: Dict) -> float:
    """Return session wall-clock duration in seconds."""
    created = session.get("created_at", time.time())
    return time.time() - created


def build_conversation_record(
    session: Dict,
    classification: str,
    reason: str,
    user_info: Dict,
) -> Dict:
    """
    Build the structured conversation JSON payload per spec.
    """
    history   = session.get("history", [])
    pages     = session.get("pages_visited", [])
    duration  = int(get_session_duration(session))
    questions = extract_questions(history)

    # Normalise transcript entries so they all have role/message/timestamp
    transcript = []
    for msg in history:
        transcript.append({
            "role":      msg.get("role", "user"),
            "message":   msg.get("content", msg.get("message", "")),
            "timestamp": msg.get("timestamp", datetime.now(timezone.utc).isoformat()),
        })

    return {
        "lead_classification":     classification,
        "classification_reason":   reason,
        "time_spent_seconds":      duration,
        "pages_navigated":         pages,
        "questions_asked":         questions,
        "profile_info": {
            "name":         user_info.get("name", "Guest"),
            "email":        user_info.get("email", ""),
            "phone_number": user_info.get("phone") or "N/A",
        },
        "conversation_transcript": transcript,
    }


# ── Storage ────────────────────────────────────────────────────────────────────

def _insert_conversation(record: Dict, classification: str) -> Optional[str]:
    """
    Insert into the lead_conversations table using the admin client.
    Returns the new UUID id, or None on failure.
    """
    from .supabase_service import insert_conversation
    return insert_conversation(
        lead_type=classification,
        conversation_content=record,
        questions_asked=record.get("questions_asked", []),
        time_spent_seconds=record.get("time_spent_seconds", 0),
        pages_navigated=record.get("pages_navigated", []),
    )


def _insert_lead(user_info: Dict, classification: str, reason: str,
                 session: Dict, conversation_id: Optional[str]) -> Optional[int]:
    """
    Insert into high_intent_leads or mid_intent_leads using the admin client.
    Returns the new row id, or None on failure.
    """
    from .supabase_service import insert_high_intent_lead, insert_mid_intent_lead

    duration = int(get_session_duration(session))
    pages    = session.get("pages_visited", [])

    payload = {
        "name":                   user_info.get("name", "Guest"),
        "email":                  user_info.get("email", ""),
        "phone_number":           user_info.get("phone") or "N/A",
        "profile_data":           {
            "id":    user_info.get("id"),
            "email": user_info.get("email"),
            "name":  user_info.get("name"),
            "phone": user_info.get("phone"),
        },
        "classification_reason":  reason,
        "time_spent_seconds":     duration,
        "pages_navigated":        pages,
        "conversation_id":        conversation_id,
    }

    if classification == "high_intent":
        return insert_high_intent_lead(payload)
    else:
        return insert_mid_intent_lead(payload)


def _update_conversation_lead_id(conversation_id: int, lead_id: int, classification: str):
    """Back-fill the lead_id on the conversation row after lead is inserted."""
    from .supabase_service import update_conversation_lead_id
    update_conversation_lead_id(conversation_id, lead_id, classification)


# ── Main pipeline ──────────────────────────────────────────────────────────────

async def run_classification_pipeline(session_id: str, session: Dict) -> str:
    """
    Full lead classification pipeline for one session.

    Returns one of: "discarded_short", "discarded_no_intent",
                    "stored_high_intent", "stored_mid_intent", "error"
    """
    from .intent_classifier import classify_user_intent

    user_info = session.get("user_info") or {}
    duration  = get_session_duration(session)
    history   = session.get("history", [])

    # ── Gate 1: minimum session duration (bypass for urgent high-intent signals)
    if duration < MIN_SESSION_SECONDS:
        # Bug 4 fix: Don't discard short sessions that contain high-intent triggers
        # (e.g. user who types "call me back" in 5 seconds is a real lead)
        from .intent_classifier import HIGH_INTENT_TRIGGERS
        all_user_text = " ".join(
            m.get("content", m.get("message", "")).lower()
            for m in history if m.get("role") == "user"
        )
        has_urgent_signal = any(t in all_user_text for t in HIGH_INTENT_TRIGGERS)
        if not has_urgent_signal:
            logger.info(
                f"[Pipeline] [{session_id}] DISCARDED — too short "
                f"({duration:.0f}s < {MIN_SESSION_SECONDS}s) with no urgent signals. Nothing stored."
            )
            return "discarded_short"
        logger.info(
            f"[Pipeline] [{session_id}] Short session ({duration:.0f}s) but has urgent signal — proceeding."
        )

    # ── Gate 2: must have at least 1 message ─────────────────────────────────
    if len(history) < 1:
        logger.info(f"[Pipeline] [{session_id}] DISCARDED — empty conversation.")
        return "discarded_short"

    logger.info(
        f"[Pipeline] [{session_id}] Qualifying session: "
        f"{duration:.0f}s duration, {len(history)} messages, "
        f"user={user_info.get('email', 'guest')}"
    )

    # ── Build payload for LLM ─────────────────────────────────────────────────
    questions = extract_questions(history)
    session_payload = {
        "chat_history":       history,
        "pages_visited":      session.get("pages_visited", []),
        "properties_viewed":  session.get("properties_viewed", 0),
        "time_spent_seconds": int(duration),
        "questions_asked":    questions,
    }

    # ── Call LLM ──────────────────────────────────────────────────────────────
    try:
        result = await classify_user_intent(session_payload)
    except Exception as e:
        logger.error(f"[Pipeline] [{session_id}] LLM call threw: {e}")
        return "error"

    if not result:
        logger.warning(f"[Pipeline] [{session_id}] LLM returned None — treating as no_intent.")
        return "discarded_no_intent"

    classification = result.get("classification", "no_intent")
    reason         = result.get("reason", "No reason provided.")

    # ── Gate 3: no_intent — discard, store nothing ────────────────────────────
    if classification == "no_intent":
        logger.info(
            f"[Pipeline] [{session_id}] DISCARDED (no_intent) — "
            f"Reason: {reason}"
        )
        return "discarded_no_intent"

    # ── Build & store conversation record ─────────────────────────────────────
    conv_record = build_conversation_record(session, classification, reason, user_info)

    conversation_id = None
    try:
        conversation_id = _insert_conversation(conv_record, classification)
        logger.info(f"[Pipeline] [{session_id}] Conversation archived — id={conversation_id}")
    except Exception as e:
        logger.error(f"[Pipeline] [{session_id}] Failed to insert conversation: {e}")

    # ── Store lead ─────────────────────────────────────────────────────────────
    lead_id = None
    try:
        lead_id = _insert_lead(user_info, classification, reason, session, conversation_id)
        logger.info(
            f"[Pipeline] [{session_id}] STORED {classification} lead — "
            f"lead_id={lead_id}, conv_id={conversation_id} | "
            f"email={user_info.get('email','?')} | Reason: {reason}"
        )
    except Exception as e:
        logger.error(f"[Pipeline] [{session_id}] Failed to insert lead: {e}")

    # ── Back-fill lead_id on conversation ─────────────────────────────────────
    if conversation_id and lead_id:
        try:
            _update_conversation_lead_id(conversation_id, lead_id, classification)
        except Exception as e:
            logger.warning(f"[Pipeline] [{session_id}] Could not back-fill lead_id: {e}")

    return f"stored_{classification}"
