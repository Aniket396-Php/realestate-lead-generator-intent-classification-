"""
Example Integration Code:
This file demonstrates how to integrate the intent_classifier.py into the existing 
FastAPI application WITHOUT modifying the core chatbot response logic.
"""

from fastapi import BackgroundTasks
from .intent_classifier import classify_user_intent

# Example of how you would call this within your existing FastAPI route
# using BackgroundTasks to ensure zero delay for the user.

async def background_intent_check(session_id: str, chat_history: list):
    """
    Background worker that collects signals and runs the classifier.
    This doesn't interfere with the response sent to the user.
    """
    
    # 1. Collect signals (in a real scenario, these 
    # would be pulled from your session/cache/request)
    session_data = {
        "chat_history": chat_history,
        "pages_visited": ["/properties", "/contact-us", "/emi-calculator"], # Example
        "properties_viewed": 4,                                           # Example
        "time_on_site": "15m"                                             # Example
    }
    
    # 2. Run the classifier
    result = await classify_user_intent(session_data)
    
    if result:
        # 3. Action on lead: Log it, send to CRM, or alert sales team
        print(f"--- LEAD ALERT ---")
        print(f"Session: {session_id}")
        print(f"Intent: {result['intent']}")
        print(f"Reason: {result['reason']}")
        print(f"------------------")


# --- How to apply to main.py ---
# In your @app.post("/chat") route, simply add:
#
# @app.post("/chat")
# async def chat(request: ChatRequest, background_tasks: BackgroundTasks):
#     # ... existing logic to get response ...
#
#     # NEW HOOK: Trigger intent classification in the background
#     history = get_session(request.session_id).get("history", [])
#     background_tasks.add_task(background_intent_check, request.session_id, history)
#
#     return response
