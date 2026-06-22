"""
Navigation handler for Property Doors chatbot.
Maps user intent to specific pages on the propertydoors.com website.
"""

import logging
import re

logger = logging.getLogger(__name__)

BASE = "https://www.propertybrix.com/en-new"

NAV_MAP = [
    (["home", "main page", "homepage", "start"],
     f"{BASE}/", "Home"),

    (["properties", "listings", "all properties", "browse"],
     f"{BASE}/properties/", "Properties"),

    (["new project", "new properties", "latest projects"],
     f"{BASE}/properties/?status=new", "New Projects"),

    (["mumbai", "properties in mumbai"],
     f"{BASE}/properties/?city=mumbai", "Mumbai Properties"),

    (["pune", "properties in pune"],
     f"{BASE}/properties/?city=pune", "Pune Properties"),

    (["bangalore", "bengaluru", "properties in bangalore"],
     f"{BASE}/properties/?city=bangalore", "Bangalore Properties"),

    (["hyderabad", "properties in hyderabad"],
     f"{BASE}/properties/?city=hyderabad", "Hyderabad Properties"),

    (["delhi", "properties in delhi"],
     f"{BASE}/properties/?city=delhi", "Delhi Properties"),

    (["ahmedabad", "properties in ahmedabad"],
     f"{BASE}/properties/?city=ahmedabad", "Ahmedabad Properties"),

    (["noida", "properties in noida"],
     f"{BASE}/properties/?city=noida", "Noida Properties"),

    (["about", "about us", "who are you", "about property doors"],
     f"{BASE}/about", "About Property Doors"),

    (["contact", "contact us", "support", "reach", "contact agent", "customer support"],
     f"{BASE}/contact", "Customer Support"),

    (["login", "sign in", "log in"],
     f"{BASE}/login", "Login"),

    (["register", "sign up", "create account", "new account"],
     f"{BASE}/register", "Sign Up"),

    (["post property", "sell", "list property", "add listing"],
     f"{BASE}/post-property", "Post Property"),

    (["wishlist", "saved", "favourites", "favorites"],
     f"{BASE}/wishlist", "Wishlist"),

    (["dashboard", "my account", "my profile", "account"],
     f"{BASE}/dashboard", "Dashboard"),

    (["blog", "articles", "news", "insights"],
     f"{BASE}/blog", "Blog"),

    (["faq", "faqs", "help", "frequently asked"],
     f"{BASE}/faq", "FAQs"),

    (["emi calculator", "loan calculator", "calculate emi", "home loan calculator", "loan services"],
     f"{BASE}/tools/emi-calculator", "Loan Services"),
]

def get_nav_options() -> list:
    return [
        {"label": "Browse Properties",  "msg": "NAV_QUERY:navigate to properties page"},
        {"label": "New Projects",        "msg": "NAV_QUERY:navigate to new projects"},
        {"label": "Post Property",       "msg": "NAV_QUERY:navigate to post property"},
        {"label": "Contact Agent",       "msg": "NAV_QUERY:navigate to contact agent"},
        {"label": "Loan Services",       "msg": "NAV_QUERY:navigate to loan services"},
        {"label": "Customer Support",    "msg": "NAV_QUERY:navigate to customer support"},
        {"label": "About Property Doors", "msg": "NAV_QUERY:navigate to about"},
        {"label": "Login / Sign In",     "msg": "NAV_QUERY:navigate to login"},
        {"label": "Create Account",      "msg": "NAV_QUERY:navigate to register"},
        {"label": "My Dashboard",        "msg": "NAV_QUERY:navigate to dashboard"}
    ]


async def get_navigation(message: str):
    msg = message.lower()
    for keywords, url, label in NAV_MAP:
        if any(kw in msg for kw in keywords):
            logger.info(f"Navigation: '{label}' for '{message[:60]}'")
            return {
                "type": "navigate",
                "url": url,
                "label": label,
                "message": f"Sure! Here's the link to the {label} page on Property Doors:",
            }

    return {
        "type": "text_response",
        "message": (
            "I'm not sure which page you're looking for. Here are some quick links:\n"
            "1. Properties — https://www.propertybrix.com/en-new/properties/\n"
            "2. About Us — https://www.propertybrix.com/en-new/about\n"
            "3. Contact — https://www.propertybrix.com/en-new/contact\n"
            "4. Post Property — https://www.propertybrix.com/en-new/post-property\n"
            "5. EMI Calculator — https://www.propertybrix.com/en-new/tools/emi-calculator"
        ),
    }
