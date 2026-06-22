# Property Brix Chatbot - Complete Workflows & Use Cases

## 📚 Table of Contents
1. [Primary Use Cases](#primary-use-cases)
2. [Detailed Workflows](#detailed-workflows)
3. [User Journeys](#user-journeys)
4. [API Request/Response Examples](#api-requestresponse-examples)
5. [Edge Cases & Error Handling](#edge-cases--error-handling)
6. [FAQ Interactions](#faq-interactions)

---

## Primary Use Cases

### Use Case 1: Property Search (Buy Apartment)
**Actor**: First-time buyer in Pune  
**Goal**: Find a 2-bedroom apartment under ₹80 lakhs  
**Complexity**: High - Multi-step funnel

### Use Case 2: FAQ Lookup
**Actor**: Existing customer  
**Goal**: Understand home loan assistance process  
**Complexity**: Low - Direct lookup

### Use Case 3: Navigation
**Actor**: User interested in posting property  
**Goal**: Navigate to "Post Property" page  
**Complexity**: Low - Direct link

### Use Case 4: Lead Scoring
**Actor**: Sales team  
**Goal**: Identify hot leads from chat behavior  
**Complexity**: High - Background analysis

### Use Case 5: Multi-Intent Session
**Actor**: Power user  
**Goal**: Search properties, ask FAQs, navigate site  
**Complexity**: High - Multiple flows in one session

---

## Detailed Workflows

### Workflow 1: Property Search Funnel (Happy Path)

```
STEP 1: USER INITIATES SEARCH
╔════════════════════════════════════════╗
║ User Input: "I want to buy a property" ║
╚════════════════════════════════════════╝
                   │
                   ▼
    ┌─────────────────────────────────────┐
    │ Intent Classification (Stage 1)     │
    │ Keyword match: "buy" + "property"   │
    │ Result: PROPERTY_SEARCH             │
    └─────────────────────────────────────┘
                   │
                   ▼
    ┌─────────────────────────────────────┐
    │ Get Session (session_id: "sess_X")  │
    │ Create if new:                      │
    │ - created_at: now()                 │
    │ - collected_data: {}                │
    │ - history: []                       │
    │ - needs_classification: true        │
    └─────────────────────────────────────┘
                   │
                   ▼
    ┌─────────────────────────────────────┐
    │ Save Message to History             │
    │ message: "I want to buy a property" │
    │ role: "user"                        │
    │ Store in sessions.json + Supabase   │
    └─────────────────────────────────────┘
                   │
                   ▼
    ┌─────────────────────────────────────┐
    │ Check Funnel: missing_field?        │
    │ Result: purpose (first field)       │
    └─────────────────────────────────────┘
                   │
                   ▼
    ┌─────────────────────────────────────┐
    │ Generate Response                   │
    │ Message: "Let's find you a property"|
    │ Options:                            │
    │  [Buy, Rent, New Projects]          │
    │ Type: text_response                 │
    └─────────────────────────────────────┘
                   │
                   ▼
    ┌─────────────────────────────────────┐
    │ Return to Frontend                  │
    │ HTTP 200 OK                         │
    │ JSON response + options             │
    └─────────────────────────────────────┘

STEP 2: USER SELECTS PURPOSE
╔════════════════════════════════════════╗
║ User Input: "Buy Property"             ║
╚════════════════════════════════════════╝
                   │
                   ▼
    ┌─────────────────────────────────────┐
    │ Intent Classification               │
    │ Keyword: "buy" in keyword set       │
    │ But in funnel context              │
    │ Intent: funnel_response             │
    └─────────────────────────────────────┘
                   │
                   ▼
    ┌─────────────────────────────────────┐
    │ Update Funnel State                 │
    │ collected_data = {                  │
    │   "purpose": "Buy Property"         │
    │ }                                   │
    │ Save to sessions.json               │
    └─────────────────────────────────────┘
                   │
                   ▼
    ┌─────────────────────────────────────┐
    │ Check Funnel: missing_field?        │
    │ Result: location (next field)       │
    └─────────────────────────────────────┘
                   │
                   ▼
    ┌─────────────────────────────────────┐
    │ Generate Response                   │
    │ Message: "Which city are you        │
    │ interested in?"                     │
    │ Options:                            │
    │  [Mumbai, Pune, Bangalore, ...]     │
    │ Type: text_response                 │
    └─────────────────────────────────────┘

STEP 3: USER SELECTS LOCATION
╔════════════════════════════════════════╗
║ User Input: "Pune"                     ║
╚════════════════════════════════════════╝
                   │
                   ▼
    ┌─────────────────────────────────────┐
    │ Update Funnel State                 │
    │ collected_data = {                  │
    │   "purpose": "Buy Property",        │
    │   "location": "Pune"                │
    │ }                                   │
    └─────────────────────────────────────┘
                   │
                   ▼
    ┌─────────────────────────────────────┐
    │ Check Funnel: missing_field?        │
    │ Result: property_type               │
    └─────────────────────────────────────┘
                   │
                   ▼
    ┌─────────────────────────────────────┐
    │ Generate Response                   │
    │ Message: "What's your preferred     │
    │ property type?"                     │
    │ Options:                            │
    │  [1BHK, 2BHK, 3BHK, Villa, Plot]   │
    │ Type: text_response                 │
    └─────────────────────────────────────┘

STEP 4: USER SELECTS PROPERTY TYPE
╔════════════════════════════════════════╗
║ User Input: "2 BHK"                    ║
╚════════════════════════════════════════╝
                   │
                   ▼
    ┌─────────────────────────────────────┐
    │ Update Funnel State                 │
    │ collected_data = {                  │
    │   "purpose": "Buy Property",        │
    │   "location": "Pune",               │
    │   "property_type": "2 BHK"          │
    │ }                                   │
    └─────────────────────────────────────┘
                   │
                   ▼
    ┌─────────────────────────────────────┐
    │ Check Funnel: missing_field?        │
    │ Result: budget                      │
    └─────────────────────────────────────┘
                   │
                   ▼
    ┌─────────────────────────────────────┐
    │ Generate Response                   │
    │ Message: "What's your budget?"      │
    │ Options:                            │
    │  [₹30L-₹50L, ₹50L-₹80L,             │
    │   ₹80L-₹1Cr, ₹1Cr+]                │
    │ Type: text_response                 │
    └─────────────────────────────────────┘

STEP 5: USER PROVIDES BUDGET (FUNNEL COMPLETE)
╔════════════════════════════════════════╗
║ User Input: "BUDGET:50L-80L"           ║
║ (Button click)                         ║
╚════════════════════════════════════════╝
                   │
                   ▼
    ┌─────────────────────────────────────┐
    │ Update Funnel State                 │
    │ collected_data = {                  │
    │   "purpose": "Buy Property",        │
    │   "location": "Pune",               │
    │   "property_type": "2 BHK",         │
    │   "budget": "50L to 80L"            │
    │ }                                   │
    │ FUNNEL COMPLETE ✓                   │
    └─────────────────────────────────────┘
                   │
                   ▼
    ┌─────────────────────────────────────┐
    │ Parse Budget String                 │
    │ Input: "50L to 80L"                 │
    │ → min_price=0.50 Cr, max_price=0.80 Cr
    │                                     │
    │ Parse Property Type                 │
    │ Input: "2 BHK"                      │
    │ → type=apartment, bedrooms=2        │
    │                                     │
    │ Parse Location                      │
    │ Input: "Pune"                       │
    │ → city=pune                         │
    └─────────────────────────────────────┘
                   │
                   ▼
    ┌─────────────────────────────────────┐
    │ Execute Query:                      │
    │ Query Supabase/properties.json:     │
    │   WHERE city = "pune"               │
    │   AND type = "apartment"            │
    │   AND bedrooms = 2                  │
    │   AND price >= 0.50                 │
    │   AND price <= 0.80                 │
    │   LIMIT 10                          │
    │                                     │
    │ Primary: Supabase                   │
    │ Fallback: properties.json           │
    │                                     │
    │ Result: 8 properties found          │
    └─────────────────────────────────────┘
                   │
                   ▼
    ┌─────────────────────────────────────┐
    │ Transform Results                   │
    │ For each property:                  │
    │  - id, title, price                 │
    │  - location, bedrooms, bathrooms    │
    │  - area_sqft, status, amenities     │
    │  - url, reason                      │
    └─────────────────────────────────────┘
                   │
                   ▼
    ┌─────────────────────────────────────┐
    │ Generate Response                   │
    │ Type: property_results              │
    │ Message: "I found 8 properties..."  │
    │ Results Array: 8 property cards     │
    │ Each card clickable for enquiry     │
    └─────────────────────────────────────┘
                   │
                   ▼
    ┌─────────────────────────────────────┐
    │ Cleanup Funnel                      │
    │ Reset collected_data = {}           │
    │ Reset current_flow = None           │
    │ Ready for next search              │
    └─────────────────────────────────────┘
                   │
                   ▼
    ┌─────────────────────────────────────┐
    │ Return to Frontend                  │
    │ HTTP 200 OK                         │
    │ JSON with 8 property results       │
    └─────────────────────────────────────┘
```

---

### Workflow 2: FAQ Lookup (Direct Path)

```
USER ASKS FAQ QUESTION
╔════════════════════════════════════════╗
║ User Input: "Are listings verified?"   ║
╚════════════════════════════════════════╝
         │
         ▼
    ┌────────────────────────────────────┐
    │ Intent Classification (Step 1)     │
    │ Keyword: "verified" in FAQ_KEYWORDS│
    │ Result: FAQ                        │
    └────────────────────────────────────┘
         │
         ▼
    ┌────────────────────────────────────┐
    │ FAQ Router (faq_rag.py)            │
    │ Keyword Map Lookup:                │
    │ "verified" → FAQ index 2           │
    └────────────────────────────────────┘
         │
         ▼
    ┌────────────────────────────────────┐
    │ Load config.json                   │
    │ Access faqs[2]                     │
    │ Question: "Are listings verified?" │
    │ Answer: "Yes. All listings on      │
    │ Property Brix are verified by our  │
    │ team. We conduct physical and      │
    │ document verification..."          │
    └────────────────────────────────────┘
         │
         ▼
    ┌────────────────────────────────────┐
    │ Generate Response                  │
    │ Type: text_response                │
    │ Message: [answer from config]      │
    │ Options:                           │
    │  [Next FAQ topics or menu]         │
    └────────────────────────────────────┘
         │
         ▼
    ┌────────────────────────────────────┐
    │ Save Interaction                   │
    │ intent: "FAQ"                      │
    │ message: "Are listings verified?"  │
    │ response: [answer]                 │
    │ → interactions.json                │
    └────────────────────────────────────┘
         │
         ▼
    ┌────────────────────────────────────┐
    │ Return to Frontend                 │
    │ HTTP 200 OK + Answer + Options     │
    └────────────────────────────────────┘
```

---

### Workflow 3: Navigation (Quick Links)

```
USER REQUESTS NAVIGATION
╔════════════════════════════════════════╗
║ User Input: "Take me to contact page"  ║
╚════════════════════════════════════════╝
         │
         ▼
    ┌────────────────────────────────────┐
    │ Intent Classification              │
    │ Keyword: "take me", "contact"      │
    │ Result: NAVIGATION                 │
    └────────────────────────────────────┘
         │
         ▼
    ┌────────────────────────────────────┐
    │ Navigation Router                  │
    │ Match message against NAV_MAP      │
    │ Find: "contact", "contact us" keys │
    │ Result: (url, label)               │
    │   url: "https://...en-new/contact" │
    │   label: "Customer Support"        │
    └────────────────────────────────────┘
         │
         ▼
    ┌────────────────────────────────────┐
    │ Generate Response                  │
    │ Type: navigate                     │
    │ url: navigation URL                │
    │ label: page title                  │
    │ message: "Sure! Here's the link to │
    │ the Customer Support page:"        │
    └────────────────────────────────────┘
         │
         ▼
    ┌────────────────────────────────────┐
    │ Return to Frontend                 │
    │ Frontend: Opens URL in new tab     │
    │ (or in iframe)                     │
    └────────────────────────────────────┘
```

---

### Workflow 4: Lead Scoring (Background Task)

```
BACKGROUND WORKER TRIGGERS (Every 30s)
╔════════════════════════════════════════╗
║ Check all sessions for idle status     ║
╚════════════════════════════════════════╝
         │
         ▼
    ┌────────────────────────────────────┐
    │ Find Idle Sessions                 │
    │ idle > 60 seconds without activity │
    │ Result: [sess_1, sess_5, sess_10]  │
    └────────────────────────────────────┘
         │
         ▼
    For each idle session {
         │
         ├─→ ┌────────────────────────────┐
         │   │ Extract Session Data:      │
         │   │ - chat_history (last 10)   │
         │   │ - pages_visited array      │
         │   │ - properties_viewed count  │
         │   │ - time_on_site (mins)      │
         │   │ - user_info (name, email)  │
         │   └────────────────────────────┘
         │         │
         │         ▼
         │   ┌────────────────────────────┐
         │   │ Build Prompt for Ollama:   │
         │   │ "Classify user intent:     │
         │   │ - HOT_LEAD: active search  │
         │   │ - NORMAL_LEAD: casual      │
         │   │ - NOT_A_LEAD: FAQ only     │
         │   │                            │
         │   │ Conversation:              │
         │   │ [history as text]          │
         │   │                            │
         │   │ Pages: [/list, /property]  │
         │   │ Properties: 3              │
         │   │ Time: 5m"                  │
         │   └────────────────────────────┘
         │         │
         │         ▼
         │   ┌────────────────────────────┐
         │   │ Call Ollama API (async)    │
         │   │ Model: phi3:latest         │
         │   │ Temperature: 0.0           │
         │   │ Format: JSON               │
         │   │ Timeout: 120s              │
         │   │                            │
         │   │ Response:                  │
         │   │ {                          │
         │   │  "intent": "HOT_LEAD",     │
         │   │  "confidence": 0.92,       │
         │   │  "reason": "User actively  │
         │   │   searched in budget,      │
         │   │   viewed 3 properties,     │
         │   │   spent 5 mins"            │
         │   │ }                          │
         │   └────────────────────────────┘
         │         │
         │         ▼
         │   ┌────────────────────────────┐
         │   │ Check Intent Result        │
         │   │ if intent in [             │
         │   │   "HOT_LEAD",              │
         │   │   "NORMAL_LEAD"            │
         │   │ ]:                         │
         │   │  → Save as Lead ✓          │
         │   │ else:                      │
         │   │  → Discard (NOT_A_LEAD)   │
         │   └────────────────────────────┘
         │         │
         │         ▼ (if qualified)
         │   ┌────────────────────────────┐
         │   │ Save Hot Lead              │
         │   │ To leads.json:             │
         │   │ {                          │
         │   │   lead_id: uuid,           │
         │   │   user_id,                 │
         │   │   email,                   │
         │   │   name,                    │
         │   │   phone,                   │
         │   │   intent: "HOT_LEAD",      │
         │   │   reason: [from LLM],      │
         │   │   session_id,              │
         │   │   timestamp,               │
         │   │   search_criteria: {...}   │
         │   │ }                          │
         │   │                            │
         │   │ Also log to Supabase       │
         │   │ (fire and forget)          │
         │   └────────────────────────────┘
         │         │
         └─→ ┌────────────────────────────┐
             │ Mark Session Classified    │
             │ session[is_classified]     │
             │ = true                     │
             │                            │
             │ Save to sessions.json      │
             └────────────────────────────┘

RESULT:
Sales team receives notification of new hot leads
Email/CRM integration with leads.json or Supabase
```

---

## User Journeys

### Journey 1: First-Time Buyer (Complete Path)

```
👤 PERSONA: Ramesh, 32, Software Engineer, First-time Buyer
🎯 GOAL: Find an apartment in Pune for ₹60-80L
⏱️ TIME: 5 minutes

┌─ SESSION START ────────────────────────────────────┐
│ Ramesh clicks "Chat with AI" on propertybrix.com   │
│ Widget opens with greeting                         │
│ Session ID: sess_a1b2c3d4e5                        │
└────────────────────────────────────────────────────┘

Message 1: "Hi"
├─ Bot: "Welcome to Property Brix! Looking to buy, rent, or invest?"
├─ Options: [MENU_FIND_PROPERTIES, MENU_ASK_FAQ, MENU_NAVIGATE]
├─ Intent: GREETING
└─ Time: 0:05

Message 2: "I want to buy a 2BHK in Pune around 60-70 lakhs"
├─ Bot: "Great! Let me help you find that."
├─ Intent: PROPERTY_SEARCH
├─ Step 1 (Purpose): "Buy" → Collected ✓
├─ Step 2 (Location): "Pune" → Collected ✓
├─ Step 3 (Type): "2BHK" → Collected ✓
├─ Step 4 (Budget): "60-70 lakhs" → Parsed as 0.60-0.70 Cr ✓
└─ Time: 0:30

FUNNEL COMPLETE → SEARCH EXECUTED
├─ Query: city=pune, type=apartment, beds=2, price=0.60-0.70
├─ Results: 6 properties found
├─ Properties displayed as cards
└─ Time: 0:45

Message 3: User clicks on Property "#3: 2 BHK in Viman Nagar"
├─ Bot: "Interested in this property? I can help you with an enquiry."
├─ Option: [Send Enquiry, View More Details]
└─ Time: 1:00

Message 4: "Yes, send enquiry"
├─ Bot: "Great! I've sent your enquiry. Our team will contact you soon."
├─ Enquiry saved to enquiries.json
├─ User receives confirmation
└─ Time: 1:15

Message 5: User browses 2 more properties but no further action
├─ Session activity tracking:
│  ├─ Pages visited: [/properties, /property/detail]
│  ├─ Properties viewed: 3
│  ├─ Time on site: 5 minutes
│  └─ Chat history: 5 messages
└─ Time: 5:00

IDLE DETECTION (after 30s inactivity)
├─ Background worker analyzes session
├─ Classification:
│  ├─ Chat: "I want to buy 2BHK... send enquiry"
│  ├─ Pages: Properties pages only
│  ├─ Properties viewed: 3
│  ├─ Time: 5 mins
│  └─ Result: HOT_LEAD (confidence: 0.95)
├─ Reason: "User completed full search funnel with specific criteria"
├─ Lead saved to leads.json
├─ Supabase log: Lead entry created
└─ Time: 5:35

📊 SESSION SUMMARY:
├─ Status: Completed ✓
├─ Lead Type: HOT_LEAD
├─ Enquiry Made: 1
├─ Properties Viewed: 3
├─ Conversion: Yes (enquiry submitted)
└─ Sales Follow-up: Required
```

---

### Journey 2: General Information Seeker

```
👤 PERSONA: Priya, 28, First-time Investor
🎯 GOAL: Understand Property Brix services before exploring
⏱️ TIME: 10 minutes

Message 1: "Hi, what is Property Brix?"
├─ Intent: FAQ
├─ Bot: [Full explanation from config.json]
└─ Time: 0:15

Message 2: "Are listings verified?"
├─ Intent: FAQ
├─ Bot: "Yes, all listings verified by our team..."
└─ Time: 0:45

Message 3: "How do I search for properties?"
├─ Intent: FAQ
├─ Bot: "You can search by typing requirements..."
└─ Time: 1:00

Message 4: "What about home loans?"
├─ Intent: FAQ
├─ Bot: "Yes! We have partnerships with 12+ banks..."
└─ Time: 1:30

Message 5: "Can I list my property?"
├─ Intent: FAQ → NAVIGATION (combined)
├─ Bot: [Overview] "Let me take you to the listing page"
├─ Navigation: Post Property URL
└─ Time: 2:00

IDLE DETECTION (after 5 mins)
├─ Analysis:
│  ├─ Chat: All FAQ questions
│  ├─ Pages: No property pages
│  ├─ Properties viewed: 0
│  ├─ Properties: FAQ only
│  └─ Result: NOT_A_LEAD
├─ Reason: "User seeking general information only"
├─ Action: No lead record created
└─ Time: 7:00

📊 SESSION SUMMARY:
├─ Status: FAQ Inquiry
├─ Lead Type: NOT_A_LEAD
├─ Properties Viewed: 0
├─ Enquiries Made: 0
├─ Conversion: No
└─ Follow-up: Informational only
```

---

### Journey 3: Multi-Intent Power User

```
👤 PERSONA: Arun, 45, Corporate Executive, Experienced Investor
🎯 GOAL: Multiple queries in one session
⏱️ TIME: 15 minutes

Message 1: "Show me luxury villas in Mumbai above 2 crore"
├─ Intent: PROPERTY_SEARCH
├─ Funnel executes: Purpose→Buy, Location→Mumbai, Type→Villa, Budget→2Cr+
├─ Result: 4 luxury villas displayed
└─ Time: 1:00

Message 2: "How long is the registration process?"
├─ Intent: FAQ (mid-search)
├─ Bot: "Typical registration takes 30-60 days..."
└─ Time: 1:30

Message 3: "Navigate to EMI calculator"
├─ Intent: NAVIGATION (while in property search)
├─ Bot: Links to loan calculator
└─ Time: 2:00

Message 4: "Go back to properties, show me commercial spaces"
├─ Intent: PROPERTY_SEARCH (new search)
├─ Previous funnel reset
├─ New funnel: Purpose→Buy, Location→Mumbai, Type→Commercial, Budget→open
├─ Result: 7 commercial properties
└─ Time: 3:30

Message 5: "Contact agent for villa inquiry"
├─ Intent: ENQUIRY (from earlier context)
├─ Bot: "Sending enquiry for first villa..."
├─ 1 enquiry created
└─ Time: 4:00

ACTIVITY TRACKING:
├─ Pages visited: [/properties, /properties-luxury, /calculator, /contact]
├─ Property types searched: Villa, Commercial
├─ Properties viewed: 11 total (4 villas + 7 commercial)
├─ Time on site: 4 minutes
├─ Enquiries: 1

IDLE DETECTION (after 1 min)
├─ Analysis:
│  ├─ Multiple searches completed
│  ├─ Inquiry placed
│  ├─ High engagement
│  ├─ Specific criteria provided
│  └─ Result: HOT_LEAD (confidence: 0.88)
├─ Reason: "Power user, multiple searches, serious inquiry placed"
└─ Lead created

📊 SESSION SUMMARY:
├─ Status: Complex Search ✓
├─ Lead Type: HOT_LEAD
├─ Properties Viewed: 11
├─ Enquiries: 1
├─ Topics: Property Search, FAQ, Navigation, Enquiry
└─ Conversion: Yes (inquiry + possible follow-up)
```

---

## API Request/Response Examples

### Request 1: Chat Message (Property Search)

```json
POST /chat HTTP/1.1
Host: property-brix-api.com
Content-Type: application/json
Content-Length: 156

{
  "message": "2 BHK in Pune under 80 lakhs",
  "session_id": "sess_b8c9d0e1f2",
  "user": {
    "id": "user_12345",
    "email": "ramesh@example.com",
    "name": "Ramesh Kumar",
    "phone": "9876543210"
  }
}
```

### Response 1: Property Search Complete

```json
HTTP/1.1 200 OK
Content-Type: application/json

{
  "type": "property_results",
  "message": "I found 8 properties matching your criteria in Pune. Here are the top results:",
  "results": [
    {
      "id": "PB001",
      "title": "2 BHK Apartment in Wakad, Pune",
      "price": "₹72L",
      "location": "Wakad",
      "bedrooms": 2,
      "bathrooms": 2,
      "area_sqft": 1050,
      "status": "ready_to_move",
      "amenities": ["Gym", "Pool", "Security"],
      "url": "https://propertybrix.com/property/PB001",
      "reason": "Perfect match for your criteria"
    },
    {
      "id": "PB002",
      "title": "2 BHK Apartment in Hinjewadi, Pune",
      "price": "₹68L",
      "location": "Hinjewadi",
      "bedrooms": 2,
      "bathrooms": 2,
      "area_sqft": 980,
      "status": "ready_to_move",
      "amenities": ["Gym", "Cafeteria", "Parking"],
      "url": "https://propertybrix.com/property/PB002",
      "reason": "Best value in budget"
    },
    {
      "id": "PB003",
      "title": "2 BHK Apartment in Viman Nagar, Pune",
      "price": "₹75L",
      "location": "Viman Nagar",
      "bedrooms": 2,
      "bathrooms": 2,
      "area_sqft": 1100,
      "status": "ready_to_move",
      "amenities": ["Gym", "Pool", "Security", "Playfield"],
      "url": "https://propertybrix.com/property/PB003",
      "reason": "Largest area in budget"
    }
  ],
  "options": [
    {"label": "🔍 Refine Search", "msg": "MENU_FIND_PROPERTIES"},
    {"label": "❓ Ask Question", "msg": "MENU_ASK_FAQ"},
    {"label": "📍 Navigate Site", "msg": "MENU_NAVIGATE"}
  ]
}
```

---

### Request 2: FAQ Query

```json
POST /chat HTTP/1.1
Host: property-brix-api.com
Content-Type: application/json

{
  "message": "FAQ_QUERY:Docompany provide home loan assistance?",
  "session_id": "sess_b8c9d0e1f2",
  "user": {
    "id": "user_12345",
    "email": "ramesh@example.com",
    "name": "Ramesh Kumar",
    "phone": "9876543210"
  }
}
```

### Response 2: FAQ Answer

```json
HTTP/1.1 200 OK
Content-Type: application/json

{
  "type": "text_response",
  "message": "Yes! We have partnerships with 12+ leading banks and NBFCs including SBI, HDFC, ICICI, and Axis Bank. Our loan advisors can help you get pre-approved and find the best interest rates for your budget.",
  "options": [
    {"label": "❓ More FAQs", "msg": "MENU_ASK_FAQ"},
    {"label": "🏠 Find Properties", "msg": "MENU_FIND_PROPERTIES"},
    {"label": "📧 Contact Support", "msg": "NAV_QUERY:navigate to contact"}
  ]
}
```

---

### Request 3: Navigation Request

```json
POST /chat HTTP/1.1
Host: property-brix-api.com
Content-Type: application/json

{
  "message": "NAV_QUERY:navigate to loan calculator",
  "session_id": "sess_b8c9d0e1f2",
  "user": {
    "id": "user_12345",
    "email": "ramesh@example.com",
    "name": "Ramesh Kumar"
  }
}
```

### Response 3: Navigation Link

```json
HTTP/1.1 200 OK
Content-Type: application/json

{
  "type": "navigate",
  "url": "https://www.propertybrix.com/en-new/tools/emi-calculator",
  "label": "Loan Services",
  "message": "Sure! Here's the link to the Loan Services page on Property Brix:",
  "options": [
    {"label": "🔙 Back to Chat", "msg": "Continue"},
    {"label": "🔍 Find Properties", "msg": "MENU_FIND_PROPERTIES"}
  ]
}
```

---

### Request 4: Enquiry Request

```json
POST /chat HTTP/1.1
Host: property-brix-api.com
Content-Type: application/json

{
  "message": "ENQUIRY:PB001",
  "session_id": "sess_b8c9d0e1f2",
  "user": {
    "id": "user_12345",
    "email": "ramesh@example.com",
    "name": "Ramesh Kumar",
    "phone": "9876543210"
  }
}
```

### Response 4: Enquiry Confirmation

```json
HTTP/1.1 200 OK
Content-Type: application/json

{
  "type": "text_response",
  "message": "Great! Your enquiry for '2 BHK Apartment in Wakad, Pune' (₹72L) has been sent. Our team will contact you shortly at 9876543210.",
  "options": [
    {"label": "🔍 Browse More", "msg": "MENU_FIND_PROPERTIES"},
    {"label": "❓ Ask FAQ", "msg": "MENU_ASK_FAQ"}
  ]
}
```

---

## Edge Cases & Error Handling

### Edge Case 1: Invalid Budget Format

```
User Input: "I have 50 to 80"
├─ Parser tries to extract unit
├─ No "lac" or "crore" found
├─ Fallback: Ask for clarification
└─ Response: "Could you specify the budget? 
               e.g., '50L to 80L' or '₹50-80 lakhs'"
```

### Edge Case 2: Unknown City

```
User Input: "I want a property in XYZ City"
├─ City lookup fails
├─ get_all_locations() returns configured cities only
├─ Options show: [Mumbai, Pune, Bangalore, ...Other Cities]
└─ User: Clicks "Other Cities" for manual entry
```

### Edge Case 3: Ollama Service Down

```
While classifying complex query:
├─ Ollama unreachable (timeout 120s)
├─ Fallback to keyword classification
├─ If no keyword match: Mark as GENERAL
├─ Continue with safe default response
└─ Log error for monitoring
```

### Edge Case 4: Session Expiry

```
User session idle for > 1 hour:
├─ Background cleaner marks for deletion
├─ If user messages again:
│  ├─ Recognize session_id but TTL expired
│  ├─ Create new session with history preserved option
│  └─ "Welcome back! Where were we?"
└─ Old interactions remain in history
```

### Edge Case 5: Large Chat History

```
Session with 50+ messages:
├─ Keep only last 10 in memory
├─ Older messages still in interactions.json
├─ For LLM context: Use last 10 only
├─ Prevents token overflow & improves performance
└─ Full history available for analytics
```

### Edge Case 6: Concurrent Requests (Race Condition)

```
Two simultaneous /chat requests, same session:
├─ Thread Lock acquired on session
├─ First request: updates funnel state
├─ Second request: waits for lock
├─ No data corruption ✓
├─ Both responses valid
└─ Interactions.lock & enquiries.lock prevent corruption
```

### Edge Case 7: No Results Found

```
Property search returns 0 results:
├─ Query: city=unknown, bedrooms=10, price=50Cr+
├─ Supabase: 0 results
├─ JSON fallback: Also 0 results
├─ Response:
│  {
│    "type": "no_results",
│    "message": "No properties found for your criteria.
│                Would you like to adjust your search?",
│    "options": [
│      {"label": "Adjust Budget", "msg": "budget"},
│      {"label": "Change Location", "msg": "location"},
│      {"label": "Ask FAQ", "msg": "MENU_ASK_FAQ"}
│    ]
│  }
└─ User can refine search
```

---

## FAQ Interactions

### Complete FAQ Tree

```
FAQs (6 categories, 20+ questions):

1. ABOUT PROPERTY BRIX
   ├─ What is Property Brix?
   ├─ Who are you?
   ├─ What services do you offer?
   └─ How long have you been operating?

2. PROPERTY SEARCH
   ├─ How do I search for properties?
   ├─ How do I filter by location/budget?
   ├─ Can I save properties?
   └─ What are advanced search filters?

3. VERIFICATION & TRUST
   ├─ Are listings verified?
   ├─ How are listings verified?
   ├─ What documents do you verify?
   └─ Is your platform RERA registered?

4. CHARGES & PRICING
   ├─ What are the listing charges?
   ├─ How much is premium listing?
   ├─ Are there buyer charges?
   ├─ What about transaction fees?
   └─ When do I pay?

5. HOME LOANS
   ├─ Do you provide home loan assistance?
   ├─ Which banks do you partner with?
   ├─ How do I apply for a loan?
   ├─ What's the approval process?
   └─ Can I calculate EMI?

6. LOGISTICS & OPERATIONS
   ├─ How do I schedule a site visit?
   ├─ How long does registration take?
   ├─ What documents are needed?
   ├─ How do I report a property issue?
   └─ What's the customer support contact?
```

---

## Summary

This chatbot provides a **seamless real estate experience** through:

✅ **Smart Intent Routing** - Keywords + LLM fallback  
✅ **Guided Property Search** - 4-step funnel  
✅ **Instant FAQ Answers** - No LLM needed  
✅ **Quick Navigation** - Links to website sections  
✅ **Lead Identification** - Background classification  
✅ **Multi-intent Handling** - Users can switch flows  
✅ **Persistence** - Sessions survive restarts  
✅ **Safety** - Thread-safe, no data corruption  
✅ **Scalability** - JSON fallback if DB fails  
✅ **Transparency** - Full audit trail

All designed for **real estate professionals** and **property hunters** in India! 🇮🇳

