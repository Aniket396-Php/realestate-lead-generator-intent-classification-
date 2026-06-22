import json
import logging
import os
import threading
from datetime import datetime
from typing import Dict, Any, Optional
from .supabase_service import log_message, log_enquiry, log_hot_lead

logger = logging.getLogger(__name__)

BASE_APP_DIR     = os.path.dirname(__file__)
DATA_DIR         = os.path.join(BASE_APP_DIR, "data")
INTERACTIONS_FILE = os.path.join(DATA_DIR, "interactions.json")
ENQUIRIES_FILE   = os.path.join(DATA_DIR, "enquiries.json")
LEADS_FILE       = os.path.join(DATA_DIR, "leads.json")


MAX_INTERACTIONS = 1000   # Bug 10 fix: keep only last 1000 records

# Bug 11 fix: one lock per file to prevent concurrent write corruption
_interactions_lock = threading.Lock()
_enquiries_lock    = threading.Lock()


def _ensure(file_path: str):
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(file_path):
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump([], f)


def _read_json(file_path: str) -> list:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _write_json(file_path: str, data: list):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def append_interaction(user_id: str, email: str, message: str,
                       intent: str, response: str, session_id: str):
    _ensure(INTERACTIONS_FILE)
    with _interactions_lock:                    # Bug 11 fix: thread-safe write
        data = _read_json(INTERACTIONS_FILE)
        data.append({
            "user_id":           user_id,
            "user_email":        email,
            "session_id":        session_id,
            "user_message":      message,       # Bug 17 fix: clean msg (no prefix)
            "classified_intent": intent,
            "bot_response":      response,
            "timestamp":         datetime.utcnow().isoformat() + "Z"
        })
        # Bug 10 fix: rotate if exceeds max size
        if len(data) > MAX_INTERACTIONS:
            data = data[-MAX_INTERACTIONS:]
        _write_json(INTERACTIONS_FILE, data)
    
    # Also log to Supabase (safe call, won't block)
    log_message(user_id, session_id, "user", message)
    log_message(user_id, session_id, "bot", response)



def save_enquiry(user_id: str, email: str, name: str, phone: str,
                 property_id: str, message: str):
    _ensure(ENQUIRIES_FILE)
    import uuid
    new_enquiry = {
        "enquiry_id":      f"enq_{uuid.uuid4().hex[:8]}",
        "user_id":         user_id,
        "customer":        {"name": name, "email": email, "phone": phone},
        "property_id":     property_id,
        "enquiry_message": message,
        "status":          "pending_notification",
        "timestamp":       datetime.utcnow().isoformat() + "Z"
    }
    with _enquiries_lock:                       # Bug 11 fix: thread-safe write
        try:
            data = _read_json(ENQUIRIES_FILE)
            data.append(new_enquiry)
            _write_json(ENQUIRIES_FILE, data)
        except Exception as e:
            logger.error(f"Failed to save enquiry: {e}")
            return None

    # Also log to Supabase (Bug fix: was unreachable due to return inside with block)
    log_enquiry(user_id, email, name, phone, property_id, message)
    return new_enquiry



def save_hot_lead(user_id: str, email: str, name: str, phone: str, 
                  classification: Dict[str, Any], session_id: str):
    """Saves high/medium intent leads with the AI's reason for the classification."""
    _ensure(LEADS_FILE)
    with _enquiries_lock: 
        try:
            data = _read_json(LEADS_FILE)
            data.append({
                "user_id": user_id,
                "name": name,
                "email": email,
                "phone": getattr(phone, "phone", phone) if phone else "N/A",
                "session_id": session_id,
                "intent": classification.get("intent"),
                "confidence": classification.get("confidence"),
                "reason": classification.get("reason"), # AI's reason
                "timestamp": datetime.utcnow().isoformat() + "Z"
            })
            _write_json(LEADS_FILE, data)
            logger.info(f"HOT LEAD SAVED: {email} | Reason: {classification.get('reason')}")
        except Exception as e:
            logger.error(f"Failed to save hot lead: {e}")
    
    # Also log to Supabase
    log_hot_lead(
        user_id=user_id, 
        email=email, 
        name=name, 
        phone=str(phone), 
        session_id=session_id,
        intent=classification.get("intent"),
        confidence=classification.get("confidence"),
        reason=classification.get("reason")
    )


