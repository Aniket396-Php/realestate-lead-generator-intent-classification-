"""
Property search module for Property Doors chatbot.
Fixes: budget range parsing (Bug 7), property type mapping (Bug 9), BHK regex (Bug 13).
"""

import json
import logging
import os
import re
from typing import Any, Dict

logger = logging.getLogger(__name__)
DATA_FILE = os.path.join(os.path.dirname(__file__), "data", "properties.json")


def _load_properties():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def get_all_locations(limit: int = 5):
    """
    Extract unique cities from properties.json dynamically.
    Returns a list of options: [{'label': '📍 City', 'msg': 'City'}, ...]
    """
    try:
        properties = _load_properties()
        cities = set()
        for p in properties:
            city = p.get("city", "").strip().title()
            if city:
                cities.add(city)
        
        sorted_cities = sorted(list(cities))
        
        options = []
        # Initial list showing limited cities + "Other"
        display_cities = sorted_cities[:limit] if limit else sorted_cities

        for city in display_cities:
            options.append({"label": f"📍 {city}", "msg": city})
            
        if limit and len(sorted_cities) > limit:
            options.append({"label": "📍 Other Cities", "msg": "OTHER_LOCATION"})
            
        return options
    except Exception as e:
        logger.error(f"Error getting dynamic locations: {e}")
        return []



def to_cr(val: str, unit: str) -> float:
    """Convert a value+unit to crores."""
    v = float(val)
    if unit and unit.lower().startswith("l"):
        return v / 100
    return v


def _parse_price(msg: str):
    """
    Returns (min_cr, max_cr) in crores or (None, None).
    Bug 7 fix: now handles structured budget strings like '50L to 80L', 'above 1Cr'.
    """
    msg = msg.lower()

    # ── Structured range: "50L to 80L", "80L to 1Cr" (from BUDGET: funnel options) ──
    range_m = re.search(
        r"(\d+(?:\.\d+)?)\s*(l|lac|lakh|cr|crore)\s+to\s+(\d+(?:\.\d+)?)\s*(l|lac|lakh|cr|crore)",
        msg)
    if range_m:
        return (to_cr(range_m.group(1), range_m.group(2)),
                to_cr(range_m.group(3), range_m.group(4)))

    # ── "above X" pattern ──
    above_m = re.search(r"above\s+(\d+(?:\.\d+)?)\s*(l|lac|lakh|cr|crore)", msg)
    if above_m:
        return to_cr(above_m.group(1), above_m.group(2)), None

    # ── Natural language: "under 80 lakh", "below 1.5 cr" ──
    under_m = re.search(
        r"(?:under|below|less than|upto|up to)\s*₹?\s*([\d.]+)\s*(l|lac|lakh|cr|crore)?", msg)
    above_nl = re.search(
        r"(?:above|more than|over|min)\s*₹?\s*([\d.]+)\s*(l|lac|lakh|cr|crore)?", msg)
    budget_m = re.search(
        r"budget\s*(?:of|is|around)?\s*₹?\s*([\d.]+)\s*(l|lac|lakh|cr|crore)?", msg)

    min_price = None
    max_price = None
    if under_m:
        max_price = to_cr(under_m.group(1), under_m.group(2))
    if above_nl:
        min_price = to_cr(above_nl.group(1), above_nl.group(2))
    if budget_m and not max_price:
        max_price = to_cr(budget_m.group(1), budget_m.group(2)) * 1.1

    return min_price, max_price


def _parse_bedrooms(msg: str):
    """Bug 13 fix: handle multi-digit BHK (e.g. '10 BHK')."""
    m = re.search(r"(\d+)\s*bhk", msg.lower())
    return int(m.group(1)) if m else None


def _parse_location(msg: str):
    CITIES = [
        "mumbai", "pune", "bangalore", "hyderabad", "delhi",
        "ahmedabad", "noida", "chennai", "thane", "bandra",
        "wakad", "hinjewadi", "whitefield", "gachibowli",
        "dwarka", "sarjapur", "bkc", "jubilee hills", "sg highway", "sector 62"
    ]
    msg_l = msg.lower()
    for city in CITIES:
        if city in msg_l:
            return city
    return None


def _parse_type(msg: str):
    """
    Bug 9 fix: map funnel property_type values (Villa, Commercial, 1 BHK etc.)
    to internal type strings.
    """
    TYPE_MAP = {
        "villa":      "villa",
        "bungalow":   "villa",
        "flat":       "apartment",
        "apartment":  "apartment",
        "flats":      "apartment",
        "plot":       "plot",
        "land":       "plot",
        "commercial": "commercial",
        "office":     "commercial",
        "shop":       "commercial",
        "studio":     "studio",
        "penthouse":  "penthouse",
    }
    msg_l = msg.lower()
    for keyword, ptype in TYPE_MAP.items():
        if keyword in msg_l:
            return ptype
    return None


def filter_properties_list(bedrooms=None, location=None, ptype=None, min_price=None, max_price=None, purpose=None) -> list:
    """Returns a raw list of property dictionaries matching the criteria."""
    properties = _load_properties()
    
    # Bug 8 fix: skip "OTHER_LOCATION" as a real location filter
    if location and location.lower() in ("other", "other_location"):
        location = None

    results = []
    print(f"Filtering {len(properties)} properties with criteria: loc={location}, type={ptype}, bed={bedrooms}, price={min_price}-{max_price}, purpose={purpose}")
    
    for p in properties:
        # 1. Purpose check
        if purpose and p.get("purpose", "").lower() != purpose.lower():
            continue
            
        # 2. Bedrooms check
        if bedrooms and p.get("bedrooms") != bedrooms:
            continue
            
        # 3. Location check
        if location:
            loc_lower = location.lower()
            if loc_lower not in p.get("city", "").lower() and loc_lower not in p.get("location", "").lower():
                continue
                
        # 4. Type check (Fuzzy)
        if ptype:
            # Match 'apartment' in 'residential apartment' or just 'apartment'
            if ptype.lower() not in p.get("type", "").lower():
                continue
                
        # 5. Price check
        p_price = float(p.get("price", 0))
        if max_price and p_price > max_price:
            continue
        if min_price and p_price < min_price:
            continue
        
        results.append(p)
    
    print(f"Filter done. Found {len(results)} matches.")
    return results


async def search_properties_from_json(message: str) -> Dict[str, Any]:
    """Original signature for free-text search; uses refactored filter logic."""
    bedrooms = _parse_bedrooms(message)
    location = _parse_location(message)
    ptype    = _parse_type(message)
    min_p, max_p = _parse_price(message)

    # Load all properties once at the top (Bug fix: avoid NameError when 'properties' used below)
    properties = _load_properties()

    results = filter_properties_list(
        bedrooms=bedrooms, 
        location=location, 
        ptype=ptype, 
        min_price=min_p, 
        max_price=max_p
    )

    # For empty free-text query, show featured
    if not message or (not bedrooms and not location and not ptype and not min_p and not max_p):
        results = properties[:4]
    
    # Create filters dict for reason generation
    filters = {"bedrooms": bedrooms, "location": location, "type": ptype, "min_price": min_p, "max_price": max_p}

    # No filters at all -> show top 4 featured
    if not any(filters.values()):
        results = properties[:4]

    if not results:
        return {
            "type": "text_response",
            "message": (
                "I couldn't find properties matching your exact criteria. "
                "Try adjusting your budget or location — or browse all listings:\n\n"
                "👉 https://www.propertybrix.com/en-new/properties/"
            ),
        }

    return {
        "type": "property_results",
        "message": f"Found {len(results)} propert{'y' if len(results)==1 else 'ies'} for you:",
        "results": [
            {
                "id":        p["id"],
                "title":     p["title"],
                "price":     p["price_label"],
                "location":  p["location"],
                "bedrooms":  p.get("bedrooms"),
                "bathrooms": p.get("bathrooms"),
                "area_sqft": p.get("area_sqft"),
                "status":    p.get("status"),
                "amenities": p.get("amenities", [])[:3],
                "url":       p.get("url", "https://www.propertybrix.com/en-new/properties/"),
                "reason":    _match_reason(p, filters),
            }
            for p in results[:5]
        ],
    }


def _match_reason(p: dict, filters: dict) -> str:
    reasons = []
    if filters.get("bedrooms"):
        reasons.append(f"{p['bedrooms']}BHK as requested")
    if filters.get("location"):
        reasons.append(f"Located in {p['location'].title()}")
    if filters.get("max_price"):
        reasons.append(f"Up to ₹{filters['max_price']:.2f}Cr")
    if filters.get("min_price"):
        reasons.append(f"From ₹{filters['min_price']:.2f}Cr")
    if p.get("status") == "Ready to Move":
        reasons.append("Ready to move in")
    return " - ".join(reasons) if reasons else "Great value for money"
