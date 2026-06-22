"""
Session state management for Property Doors chatbot.
Fixes: Bug 5 (file-based persistence), Bug 18 (session expiry cleanup).
"""

import json
import logging
import os
import time
import threading
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

SESSION_TTL  = 3600        # Bug 18: expire sessions after 1 hour of inactivity
SESSION_FILE = os.path.join(os.path.dirname(__file__), "data", "sessions.json")

_lock: threading.Lock = threading.Lock()


def _load_from_file() -> Dict[str, Dict[str, Any]]:
    """Bug 5 fix: restore sessions from disk on startup.
    Bug 2 fix: reset is_classified on load so sessions with history
    can be re-evaluated after a server restart.
    """
    try:
        if os.path.exists(SESSION_FILE):
            with open(SESSION_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Reset classified state for sessions that have history
            # so the background worker can re-evaluate them after restart
            reset_count = 0
            for sid, s in data.items():
                if s.get("is_classified") and len(s.get("history", [])) > 0:
                    s["is_classified"] = False
                    s["needs_classification"] = True
                    reset_count += 1
            logger.info(f"Restored {len(data)} sessions from disk ({reset_count} reset for re-classification).")
            return data
    except Exception as e:
        logger.warning(f"Could not load sessions file: {e}")
    return {}


def _save_to_file(store: Dict):
    """Bug 5 fix: persist sessions to disk."""
    try:
        os.makedirs(os.path.dirname(SESSION_FILE), exist_ok=True)
        with open(SESSION_FILE, "w", encoding="utf-8") as f:
            json.dump(store, f, ensure_ascii=False)
    except Exception as e:
        logger.warning(f"Could not save sessions: {e}")


# Load on import (fixes Bug 5 — survives server restart)
_SESSION_STORE: Dict[str, Dict[str, Any]] = _load_from_file()


def _new_session() -> Dict[str, Any]:
    return {
        "created_at":    time.time(),
        "last_active":   time.time(),
        "collected_data": {},
        "history":       [],
        "current_flow":  None,
        "user_info":     None,  # Store user details for delayed classification
        "pages_visited": [],    # Bug fix: track real pages
        "properties_viewed": 0, # Bug fix: track real property views
        "needs_classification": True, # Flag for background worker
        "is_classified": False
    }


def get_session(session_id: str, user_info: Optional[Dict] = None) -> Dict[str, Any]:
    with _lock:
        if session_id not in _SESSION_STORE:
            _SESSION_STORE[session_id] = _new_session()
        
        session = _SESSION_STORE[session_id]
        session["last_active"] = time.time()
        
        # Update user info if provided (ensure we have identity for the lead)
        if user_info:
            session["user_info"] = user_info
            
        return session


def add_message_to_history(session_id: str, role: str, content: str):
    """
    Appends a message to the session history (full transcript — no trim,
    so the complete conversation can be archived for lead classification).
    """
    session = get_session(session_id)
    with _lock:
        import datetime as _dt
        session["history"].append({
            "role":      role,
            "content":   content,
            "timestamp": _dt.datetime.utcnow().isoformat() + "Z"
        })
    _save_to_file(_SESSION_STORE)   # persist after every message


def get_missing_sales_criteria(session_id: str) -> Optional[str]:
    """
    Returns the next required funnel field that has not been collected yet.
    Flow: purpose → location → property_type → budget
    """
    session = get_session(session_id)
    data    = session.get("collected_data", {})
    for field in ("purpose", "location", "property_type", "budget"):
        if field not in data:
            return field
    return None


def generate_sales_prompt(missing_field: str, existing_data: Dict[str, Any]) -> str:
    prompts = {
        "purpose":       "Great! Let's find the right property for you.",
        "location":      "Which city are you looking in?",
        "property_type": "What type of property are you looking for?",
        "budget":        "What is your budget range?",
    }
    return prompts.get(missing_field, "Searching for properties...")


def cleanup_expired_sessions():
    """Bug 18 fix: remove sessions inactive for more than SESSION_TTL seconds."""
    now = time.time()
    with _lock:
        expired = [sid for sid, s in _SESSION_STORE.items()
                   if now - s.get("last_active", 0) > SESSION_TTL]
        for sid in expired:
            del _SESSION_STORE[sid]
    if expired:
        logger.info(f"Expired {len(expired)} stale sessions.")
        _save_to_file(_SESSION_STORE)


def get_sessions_to_classify(idle_seconds: int = 60):
    """
    Returns list of (session_id, session_data) for sessions that have been 
    inactive for idle_seconds and haven't been classified yet.
    """
    now = time.time()
    to_process = []
    with _lock:
        for sid, s in _SESSION_STORE.items():
            if (not s.get("is_classified") 
                and s.get("needs_classification")
                and (now - s.get("last_active", 0)) > idle_seconds):
                to_process.append((sid, s))
    return to_process


def update_session_activity(session_id: str, pages: List[str] = None, properties_viewed: int = 0):
    """Updates the activity tracking for a session without bumping last_active."""
    with _lock:
        if session_id not in _SESSION_STORE:
            _SESSION_STORE[session_id] = _new_session()
        session = _SESSION_STORE[session_id]
        
        if pages:
            # Union of pages visited
            existing_pages = set(session.get("pages_visited", []))
            existing_pages.update(pages)
            session["pages_visited"] = list(existing_pages)
        
        if properties_viewed > 0:
            # Keep the max count reported or increment
            session["properties_viewed"] = max(session.get("properties_viewed", 0), properties_viewed)
    
    _save_to_file(_SESSION_STORE)


def get_session_duration_seconds(session_id: str) -> float:
    """Returns total wall-clock seconds the session has been alive."""
    with _lock:
        session = _SESSION_STORE.get(session_id, {})
        created = session.get("created_at", time.time())
        return time.time() - created


def mark_session_classified(session_id: str):
    with _lock:
        if session_id in _SESSION_STORE:
            _SESSION_STORE[session_id]["is_classified"] = True
            _SESSION_STORE[session_id]["needs_classification"] = False
    _save_to_file(_SESSION_STORE)
