from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class UserProfile(BaseModel):
    id: str
    email: str
    name: Optional[str] = "Guest"
    phone: Optional[str] = None

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"
    user: Optional[UserProfile] = None
    
class EnquiryRequest(BaseModel):
    property_id: str
    message: Optional[str] = "I am interested in this property. Please contact me."
    user: UserProfile
