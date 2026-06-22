# Property Brix AI Chatbot - Complete Analysis

## 📋 Project Overview

**Property Brix AI Chatbot v2** is a FastAPI-powered conversational AI system designed to help real estate customers search for properties, get answers to FAQs, and navigate the Property Brix platform. It uses intelligent intent classification, property search constraints, and lead scoring to provide a personalized experience.

**Key Version**: 2.0.0  
**Primary Location**: Property Brix India (8 major cities)  
**Tech Stack**: Python 3.x, FastAPI, Ollama LLM, Supabase, JavaScript (Frontend Widget)

---

## 🏗️ Architecture Overview

```
propertybrix-chatbot/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI app, chat endpoint, funnel logic
│   │   ├── models.py               # Pydantic request/response schemas
│   │   ├── intent.py               # Intent classifier (keyword + LLM fallback)
│   │   ├── intent_classifier.py    # Lead scoring classifier (Ollama-based)
│   │   ├── property_search.py      # Property search logic, filtering
│   │   ├── faq_rag.py              # FAQ lookup & responses
│   │   ├── navigation.py           # Website navigation handler
│   │   ├── state.py                # Session state management (file-based)
│   │   ├── storage.py              # Persistence (interactions, enquiries, leads)
│   │   ├── supabase_client.py      # Supabase connection
│   │   ├── supabase_service.py     # Supabase queries & logging
│   │   ├── data/
│   │   │   ├── config.json         # Company info, FAQ list, cities, property types
│   │   │   ├── properties.json     # Property catalog (fallback to JSON if DB fails)
│   │   │   ├── sessions.json       # Active sessions state (persisted)
│   │   │   ├── interactions.json   # Chat history (last 1000)
│   │   │   ├── enquiries.json      # User property inquiries
│   │   │   └── leads.json          # Hot leads identified by classifier
│   │   └── __pycache__/
│   ├── requirements.txt             # Dependencies
│   └── venv/                        # Python virtual environment
├── frontend/
│   ├── chatbot-embed.js            # Embeddable widget (685 lines)
│   ├── demo.html                   # Demo page
│   ├── login.html                  # Login page
│   └── signup.html                 # Signup page
├── Makefile                         # Development commands
└── Test files (test_*.py)          # Unit and integration tests
```

---

## 🔑 Core Components

### 1. **FastAPI Application** (`main.py`)

**Port**: 8001 (configurable)  
**Endpoints**: `/chat`, `/health`, `/widget.js`, `/`

#### Key Features:
- **Session Management**: Maintains user sessions with file-based persistence
- **Intent Classification Worker**: Background task that classifies user intent 3 minutes after they go idle
- **Funnel-Based Search**: Guides users through 4 steps: Purpose → Location → Property Type → Budget
- **CORS Enabled**: Allows cross-origin requests for embedded widget

#### Main Flow:
```
User Message → Intent Classification → Route to Handler → Response + Options
```

**Handlers**:
- `MENU_*` prefixes: Direct menu selection
- `FAQ_QUERY:*`: FAQ lookup
- `NAV_QUERY:*`: Navigation
- `BUDGET:*`: Budget selection (structured format)
- Regular texts: Natural language intent detection

---

### 2. **Intent Classification** (`intent.py` + `intent_classifier.py`)

#### Two-Stage Classification:

**Stage 1: Keyword Matching** (instant, 100% reliable)
- **GREETING**: "hi", "hello", "hey" (≤4 words)
- **GRATITUDE**: "thanks", "bye", "got it" (≤6 words)
- **NAVIGATION**: "go to", "take me", "navigate", "login", "login", "dashboard"
- **FAQ**: "loan", "charges", "how do i", "what is", "contact", "site visit"
- **PROPERTY_SEARCH**: "bhk", "flat", "buy", "budget", "lakh", "crore", location names
- **GENERAL**: Default

**Stage 2: Ollama LLM** (fallback for complex queries)
- Used only if keyword match is unclear
- Model: `phi3:latest` (configurable via `LLM_MODEL` env var)
- Uses Ollama running at `http://localhost:11434`

#### Lead Classification (`intent_classifier.py`):
- Analyzes session behavior after user is idle
- Returns: **HOT_LEAD** | **NORMAL_LEAD** | **NOT_A_LEAD**
- Factors: Chat history, pages visited, properties viewed, time on site
- Triggers database save if lead qualified

---

### 3. **Property Search** (`property_search.py`)

#### Search Logic:
1. **Parse Budget**: Handles multiple formats
   - Structured: "50L to 80L", "1Cr to 2Cr"
   - Natural language: "under 80 lakh", "above 1 crore"
   - Returns (min_price_cr, max_price_cr) tuple

2. **Parse BHK**: "2 BHK" → bedrooms=2, type="apartment"

3. **Location Mapping**: City names to property city field

4. **Query Execution**:
   - Primary: Supabase database (15 fields per property)
   - Fallback: Local `properties.json` if DB fails/no results
   - Returns up to 10 results

#### Bug Fixes Applied:
- **Bug 7**: Fixed budget range parsing (e.g., "30L to 80L")
- **Bug 9**: Property type mapping (BHK → apartment)
- **Bug 13**: BHK regex extraction

---

### 4. **FAQ System** (`faq_rag.py`)

**Optimization**: No LLM needed for FAQs!

#### Features:
- **Instant Keyword Lookup**: Maps keywords to config.json FAQ index
- **Smart Matching**: Substring matching on keywords
- **LLM Fallback**: Only if question not found in FAQ list
- **UI Options**: Shows top 6 FAQs as buttons with `FAQ_QUERY:` prefix

#### FAQ Topics Covered:
1. "What is Property Brix?"
2. "How do I search for properties?"
3. "Are the listings verified?"
4. "What are charges for listing?"
5. "Do you provide home loan assistance?"
6. "How do I schedule a site visit?"
+ More...

---

### 5. **Navigation** (`navigation.py`)

**Navigation Map**: 20+ destination routes

#### Examples:
```
"go to properties" → https://www.propertybrix.com/en-new/properties/
"navigate to login" → https://www.propertybrix.com/en-new/login
"contact agent" → https://www.propertybrix.com/en-new/contact
"new projects" → https://www.propertybrix.com/en-new/properties/?status=new
"mumbai properties" → https://www.propertybrix.com/en-new/properties/?city=mumbai
```

**8 Major Cities Supported**:
Mumbai, Pune, Bangalore, Hyderabad, Delhi, Ahmedabad, Chennai, Noida

---

### 6. **Session State Management** (`state.py`)

**Storage**: File-based (`sessions.json`)

#### Session Structure:
```python
{
    "created_at": timestamp,
    "last_active": timestamp,
    "collected_data": {
        "purpose": "Buy Property",
        "location": "Pune",
        "property_type": "2 BHK",
        "budget": "50L to 80L"
    },
    "history": [
        {"role": "user", "content": "Hello"},
        {"role": "bot", "content": "Hi! Looking for..."}
    ],
    "current_flow": "property_search",
    "user_info": {...},
    "is_classified": False
}
```

#### Funnel Flow:
1. **Purpose**: Buy | Rent | New Projects
2. **Location**: Dynamic list from properties (Mumbai, Pune, etc.)
3. **Property Type**: 1BHK, 2BHK, 3BHK, Villa, Plot, Office, Commercial, Penthouse
4. **Budget**: ₹30L–₹50L | ₹50L–₹80L | ₹80L–₹1Cr | ₹1Cr+

**Bug Fixes**:
- **Bug 5**: Sessions persisted to disk (survive server restarts)
- **Bug 18**: auto-expire sessions after 1 hour inactivity

---

### 7. **Data Persistence** (`storage.py`)

**Files Managed**:
- `interactions.json`: Chat logs (last 1000 max)
- `enquiries.json`: Property inquiries
- `leads.json`: Qualified leads

#### Thread Safety:
- One lock per file (`_interactions_lock`, `_enquiries_lock`)
- Prevents concurrent write corruption
- **Bug 11 fix**: Proper locking implemented

#### Supabase Integration:
- Logs to remote `conversations` table
- Logs enquiries & hot leads
- Fallback: Continues if DB fails

**Bug Fixes**:
- **Bug 10**: Max 1000 interactions stored (rotate old ones)
- **Bug 11**: Thread-safe writes
- **Bug 17**: Store clean messages (no internal prefixes)

---

### 8. **Frontend (Embeddable Widget)** (`chatbot-embed.js`)

**Integration**: 2 lines of code

```html
<script>
  window.CHATBOT_CONFIG = { apiUrl: "http://YOUR_SERVER:8001" };
</script>
<script src="http://YOUR_SERVER:8001/widget.js" defer></script>
```

#### Features:
- **Floating Button**: Fixed position bottom-right with pulse animation
- **Chat Window**: 385×590px, clean Material Design
- **Activity Tracking**:
  - Pages visited
  - Properties viewed count
  - Session duration
  - Chat history
- **User Context**: Captures email, name, phone for leads
- **Responsive**: Mobile-friendly
- **Customizable**: Primary color, company name

#### UI Flow:
1. Message input + send button
2. Dynamic button options (funnel steps, FAQs, navigation)
3. Property results with images, price, location
4. Enquiry form for property interest

---

## 🔄 Chat Flow Example

### Scenario: Property Search (Buy 2BHK in Pune under ₹80L)

```
User: "Hi"
→ Intent: GREETING
← Response: "Hi! Welcome to Property Brix..."
← Options: [MENU_FIND_PROPERTIES, MENU_ASK_FAQ, MENU_NAVIGATE]

User: "MENU_FIND_PROPERTIES"
→ Intent: PROPERTY_SEARCH
← Message: "Great! Let's find the right property for you."
← Options: [Buy, Rent, New Projects]

User: "Buy Property"
→ Funnel collected: {purpose: "Buy Property"}
← Missing: location
← Message: "Which city are you interested in?"
← Options: [Mumbai, Pune, Bangalore, Other...]

User: "Pune"
→ Funnel collected: {location: "Pune"}
← Missing: property_type
← Message: "What's your preferred property type?"
← Options: [1BHK, 2BHK, 3BHK, Villa, ...]

User: "2 BHK"
→ Funnel collected: {property_type: "2 BHK"}
← Missing: budget
← Message: "What's your budget?"
← Options: [₹30L-₹50L, ₹50L-₹80L, ₹80L-₹1Cr, ₹1Cr+]

User: "BUDGET:50L-80L"
→ All criteria collected
→ Query Supabase/JSON:
   city=pune, type=apartment, bedrooms=2, price=0.50-0.80 Cr
← Returns: 8 properties
← Display: Cards with title, price (₹65L), location, bhk, area_sqft, status
```

---

## 📊 Data Files

### `config.json`
```json
{
  "company_name": "Property Brix",
  "phone": "+91 98765 43210",
  "email": "support@propertybrix.com",
  "locations": ["Mumbai", "Pune", ...],
  "property_types": ["Apartment", "Villa", "Plot", ...],
  "faqs": [
    {"question": "What is Property Brix?", "answer": "..."},
    ...
  ]
}
```

### `properties.json`
Property catalog with 400+ entries:
```json
[
  {
    "id": "PB001",
    "title": "2 BHK Apartment in Bandra, Mumbai",
    "city": "mumbai",
    "type": "apartment",
    "bedrooms": 2,
    "bathrooms": 2,
    "area_sqft": 1200,
    "price": 0.75,  // in Crores
    "price_label": "₹75L",
    "location": "Bandra",
    "status": "ready_to_move",
    "amenities": ["Gym", "Pool"],
    ...
  },
  ...
]
```

### `enquiries.json` (Sample)
```json
{
  "enquiry_id": "enq_3abfcb1c",
  "user_id": "test-user-123",
  "customer": {
    "name": "Test User",
    "email": "test@example.com",
    "phone": "9876543210"
  },
  "property_id": "PB004",
  "status": "pending_notification",
  "timestamp": "2026-03-10T11:06:27Z"
}
```

---

## 🚀 API Endpoints

### POST `/chat`
**Request**:
```json
{
  "message": "Show me 2BHK flats in Pune",
  "session_id": "sess_abc123",
  "user": {
    "id": "user_123",
    "email": "john@example.com",
    "name": "John",
    "phone": "9876543210"
  }
}
```

**Response Types**:
1. **text_response**: Chat message + option buttons
2. **property_results**: Property cards array
3. **navigate**: Redirect URL
4. **faq_response**: FAQ answer

### GET `/health`
Returns: `{"status": "ok", "version": "2.0.0"}`

### GET `/` (demo.html)
Interactive demo page with embedded chatbot

### GET `/widget.js`
Embeddable widget JavaScript (no-cache)

---

## 🔧 Dependencies

**Backend** (`requirements.txt`):
- `fastapi==0.111.0` - Web framework
- `uvicorn[standard]==0.29.0` - ASGI server
- `httpx==0.27.0` - Async HTTP client (for Ollama)
- `python-dotenv==1.0.1` - Environment variables
- `pydantic==2.7.1` - Data validation
- `supabase==2.4.6` - Database client

**Optional**:
- Ollama (running locally for LLM inference)
- Supabase account (for remote logging/queries)

---

## 📝 Key Bugs Fixed

| Bug # | Issue | Fix | Status |
|-------|-------|-----|--------|
| 5 | Sessions lost on restart | File-based persistence (`sessions.json`) | ✅ |
| 7 | Budget parsing fails | Regex for "50L to 80L" format | ✅ |
| 9 | Property type mismatch | BHK → apartment mapping | ✅ |
| 10 | Interactions file grows unbounded | Cap at 1000, rotate old | ✅ |
| 11 | Concurrent writes corrupt data | Added threading locks | ✅ |
| 13 | BHK extraction fails | Improved regex | ✅ |
| 17 | Internal prefixes in chat logs | Strip "FAQ_QUERY:", "NAV_QUERY:" | ✅ |
| 18 | Sessions never expire | Auto-expire after 1h inattivity | ✅ |
| 19 | Funnel answers not saved before check | Save before calling `_run_funnel()` | ✅ |

---

## 🎯 Lead Scoring System

**Background Worker** (runs every 30 seconds):
1. Checks for sessions idle > 60 seconds
2. Analyzes chat history, pages visited, properties viewed, time on site
3. Uses Ollama to classify intent:
   - **HOT_LEAD**: Actively specified criteria + urgency signals
   - **NORMAL_LEAD**: Completed search funnel
   - **NOT_A_LEAD**: General FAQs, casual browsing
4. Saves qualified leads to `leads.json` + Supabase

**Purpose**: Identify genuine buyers/renters for sales follow-up

---

## 🔐 Supabase Integration

**Optional** - Fallback to JSON if unavailable

**Tables**:
- `conversations`: Chat messages (user_id, role, message, timestamp)
- `properties`: Property listing (query for search results)
- `enquiries`: User property inquiries
- `leads`: Hot leads with classification reason

**Queries**:
- Filter by city, property type, bedrooms, price range
- Limit 10 results

---

## ⚙️ Environment Variables

```bash
# Optional
OLLAMA_BASE_URL=http://localhost:11434    # Ollama server
LLM_MODEL=phi3:latest                      # Model to use
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
```

---

## 🧪 Testing

**Test Files**:
- `test_all.py` - End-to-end funnel + FAQ + navigation
- `test_classifier.py` - Intent classifier accuracy
- `test_coverage.py` - Code coverage
- `test_env.py` - Environment validation
- `test_workflow_api.py` - API endpoint tests

**Running Tests**:
```bash
make install
python test_all.py
```

---

## 📦 Deployment

### Local Development
```bash
make venv           # Create virtual env
make install        # Install dependencies
make start          # Run on http://localhost:8001
```

### Production
```bash
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --workers 4
```

### Embedding Widget
```html
<script>
  window.CHATBOT_CONFIG = { 
    apiUrl: "https://your-domain.com:8001",
    companyName: "Your Company",
    primaryColor: "#4ADE80"
  };
</script>
<script src="https://your-domain.com:8001/widget.js"></script>
```

---

## 📊 Metrics & Monitoring

**Logs Location**: Console + JSON files in `backend/app/data/`

**Key Metrics**:
- Chat messages processed
- Intent distribution (GREETING, PROPERTY_SEARCH, FAQ, etc.)
- Property searches completed
- Leads identified (HOT_LEAD, NORMAL_LEAD)
- Session duration
- Widget impressions

---

## 🎨 UI/UX Flow

### Funnel Visualization
```
START
  ↓
[Purpose] Buy / Rent / New Projects
  ↓
[Location] Mumbai / Pune / Bangalore / ...
  ↓
[Type] 1BHK / 2BHK / 3BHK / Villa / Plot / ...
  ↓
[Budget] ₹30L-₹50L / ₹50L-₹80L / ₹80L-₹1Cr / ₹1Cr+
  ↓
SEARCH & DISPLAY RESULTS
```

### Widget UI Zones
- **Header**: Company logo + "AI Assistant"
- **Message Area**: Chat scrollable area
- **Input Bar**: Text input + send button
- **Options**: Dynamic buttons for funnel/FAQ/nav
- **Results**: Property cards (image, title, price, location, btn)

---

## 🔮 Future Enhancements

1. **Multi-language Support**: Hindi, Tamil, Telugu
2. **Advanced Filters**: Possession date, amenities, builder
3. **Comparison Tool**: Side-by-side property comparison
4. **Video Tours**: 3D property walkthroughs
5. **EMI Calculator**: Integrated loan calculator
6. **Agent Connection**: Direct chat with listing agents
7. **Notifications**: Price drop alerts, new listings
8. **Analytics Dashboard**: Lead conversion funnel, ROI

---

## 📞 Support & Contact

- **Email**: support@propertybrix.com
- **Phone**: +91 98765 43210
- **Working Hours**: Mon-Sat, 9AM - 7PM IST
- **Website**: https://www.propertybrix.com/en-new/

---

**Last Updated**: March 19, 2026  
**Version**: 2.0.0 (Clean Routing, Bug Fixes, Lead Scoring)  
**Status**: Production Ready ✅
