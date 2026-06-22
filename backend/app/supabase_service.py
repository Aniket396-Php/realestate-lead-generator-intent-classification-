import logging
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from .supabase_client import supabase, supabase_admin

logger = logging.getLogger(__name__)

# Regex to validate proper UUID format (8-4-4-4-12 hex)
_UUID_RE = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
    re.IGNORECASE
)

def _is_uuid(value: str) -> bool:
    """Return True only for proper UUID strings (not guest_ prefixed IDs)."""
    return bool(_UUID_RE.match(str(value or '')))


def log_message(user_id: str, session_id: str, role: str, message: str):
    """Log a chat message to Supabase."""
    if not supabase_admin: return
    try:
        data = {
            "user_id": user_id if _is_uuid(user_id) else None,
            "session_id": session_id,
            "role": role,
            "message": message
        }
        supabase_admin.table("conversations").insert(data).execute()
    except Exception as e:
        logger.warning(f"Error logging message to Supabase: {e}")

# DB purpose values: 'buy', 'rent', 'new_project'
_PURPOSE_MAP = {
    "buy property": "buy",
    "buy": "buy",
    "rent property": "rent",
    "rent": "rent",
    "new projects": "new_project",
    "new_project": "new_project",
    "new project": "new_project",
}

def get_properties(city: str = None, ptype: str = None, bedrooms: int = None, min_price: float = None, max_price: float = None, purpose: str = None):
    """Query properties from Supabase database."""
    if not supabase: 
        from .property_search import filter_properties_list
        return filter_properties_list(location=city, ptype=ptype, bedrooms=bedrooms, min_price=min_price, max_price=max_price, purpose=purpose)
    try:
        query = supabase.table("properties").select(
            "id,title,type,purpose,bedrooms,bathrooms,area_sqft,price,price_label,location,city,status,possession,amenities,rera,url"
        )
        
        if city:
            city_val = city.strip().lower()
            query = query.or_(f"city.ilike.%{city_val}%,location.ilike.%{city_val}%")
        if ptype:
            query = query.eq("type", ptype)
        if purpose:
            # Normalize funnel labels to DB values: "Buy Property" -> "buy"
            db_purpose = _PURPOSE_MAP.get(purpose.lower().strip(), purpose.lower().strip())
            query = query.eq("purpose", db_purpose)
            print(f"[Supabase] Purpose: '{purpose}' -> '{db_purpose}'")
        if bedrooms:
            query = query.eq("bedrooms", int(bedrooms))
        if min_price is not None and min_price > 0:
            query = query.gte("price", float(min_price))
        if max_price is not None and max_price < 900:
            query = query.lte("price", float(max_price))
            
        print(f"[Supabase] Query: city={city}, type={ptype}, bedrooms={bedrooms}, price={min_price}-{max_price}, purpose={purpose}")
        result = query.limit(10).execute()
        print(f"[Supabase] Results: {len(result.data) if hasattr(result, 'data') and result.data else 0}")
        return result.data if hasattr(result, 'data') and result.data else []

    except Exception as e:
        print(f"[Supabase] Error fetching properties: {e}")
        import traceback
        traceback.print_exc()
        return []

def log_user_activity(user_id: str, pages: List[str], properties_viewed: int, time_spent: str):
    """Log user browsing behavior to Supabase."""
    if not supabase_admin: return
    try:
        data = {
            "user_id": user_id if _is_uuid(user_id) else None,
            "pages_visited": pages,
            "properties_viewed": properties_viewed,
            "time_spent": time_spent
        }
        supabase_admin.table("user_activity").insert(data).execute()
    except Exception as e:
        logger.warning(f"Error logging activity to Supabase: {e}")

def log_enquiry(user_id: str, email: str, name: str, phone: str, property_id: str, message: str):
    """Log a property enquiry to Supabase."""
    if not supabase_admin: return
    try:
        data = {
            "user_id": user_id if _is_uuid(user_id) else None,
            "email": email,
            "name": name,
            "phone": phone,
            "property_id": property_id,
            "message": message
        }
        supabase_admin.table("enquiries").insert(data).execute()
    except Exception as e:
        logger.warning(f"Error logging enquiry to Supabase: {e}")

def log_hot_lead(user_id: str, email: str, name: str, phone: str, session_id: str, intent: str, confidence: float, reason: str):
    """Log a scored lead to Supabase."""
    if not supabase_admin: return
    try:
        data = {
            "user_id": user_id if _is_uuid(user_id) else None,
            "email": email,
            "name": name,
            "phone": phone,
            "session_id": session_id,
            "intent_level": intent,
            "confidence": confidence,
            "reason": reason
        }
        supabase_admin.table("hot_leads").insert(data).execute()
    except Exception as e:
        logger.warning(f"Error logging lead to Supabase: {e}")


# ── New lead classification storage (uses admin client to bypass RLS) ──────────

def insert_conversation(
    lead_type: str,
    conversation_content: Dict,
    questions_asked: List[str],
    time_spent_seconds: int,
    pages_navigated: List[str],
) -> Optional[str]:
    """Insert a conversation record into lead_conversations. Returns new UUID id or None."""
    if not supabase_admin:
        logger.warning("[Supabase] supabase_admin not available — conversation not stored.")
        return None
    try:
        row = {
            "lead_type":             lead_type,
            "conversation_content":  conversation_content,
            "questions_asked":       questions_asked,
            "time_spent_seconds":    time_spent_seconds,
            "pages_navigated":       pages_navigated,
        }
        res = supabase_admin.table("lead_conversations").insert(row).execute()
        if res.data:
            return res.data[0].get("id")
        logger.error(f"[Supabase] insert_conversation — no data in response: {res}")
        return None
    except Exception as e:
        logger.error(f"[Supabase] insert_conversation failed: {e}")
        return None


def insert_high_intent_lead(payload: Dict) -> Optional[int]:
    """Insert into high_intent_leads. Returns new row id or None."""
    if not supabase_admin:
        logger.warning("[Supabase] supabase_admin not available — lead not stored.")
        return None
    try:
        res = supabase_admin.table("high_intent_leads").insert(payload).execute()
        if res.data:
            lead_id = res.data[0].get("id")
            logger.info(f"[Supabase] high_intent_lead stored — id={lead_id}, email={payload.get('email')}")
            return lead_id
        logger.error(f"[Supabase] insert_high_intent_lead — no data in response: {res}")
        return None
    except Exception as e:
        logger.error(f"[Supabase] insert_high_intent_lead failed: {e}")
        return None


def insert_mid_intent_lead(payload: Dict) -> Optional[int]:
    """Insert into mid_intent_leads. Returns new row id or None."""
    if not supabase_admin:
        logger.warning("[Supabase] supabase_admin not available — lead not stored.")
        return None
    try:
        res = supabase_admin.table("mid_intent_leads").insert(payload).execute()
        if res.data:
            lead_id = res.data[0].get("id")
            logger.info(f"[Supabase] mid_intent_lead stored — id={lead_id}, email={payload.get('email')}")
            return lead_id
        logger.error(f"[Supabase] insert_mid_intent_lead — no data in response: {res}")
        return None
    except Exception as e:
        logger.error(f"[Supabase] insert_mid_intent_lead failed: {e}")
        return None


def update_conversation_lead_id(conversation_id: str, lead_id: int, classification: str):
    """Back-fill the lead_id field on the lead_conversations row."""
    if not supabase_admin:
        return
    try:
        supabase_admin.table("lead_conversations") \
            .update({"lead_id": lead_id}) \
            .eq("id", conversation_id) \
            .execute()
        logger.debug(f"[Supabase] lead_conversations.lead_id updated — conv={conversation_id}, lead={lead_id}")
    except Exception as e:
        logger.warning(f"[Supabase] update_conversation_lead_id failed: {e}")


