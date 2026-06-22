# Property Brix Chatbot - Architecture & System Design

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE LAYER                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌──────────────────┐           ┌──────────────────┐    ┌───────────────┐  │
│  │  Web Browser     │           │  Embedded Widget │    │  Mobile App   │  │
│  │  (demo.html)     │           │  (chatbot-       │    │  (Web View)   │  │
│  │                  │           │   embed.js)      │    │               │  │
│  └────────┬─────────┘           └────────┬─────────┘    └───────┬───────┘  │
│           │                              │                       │          │
│           └──────────────────┬───────────┘───────────────────────┘          │
│                              │ HTTP/CORS                                    │
└──────────────────────────────┼────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      API GATEWAY LAYER (FastAPI)                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  Port 8001  ┌────────────────────────────────────────────────────────────┐  │
│             │  POST /chat        ← Main chat endpoint                    │  │
│             │  GET  /health      ← Health check                          │  │
│             │  GET  /widget.js   ← Embeddable widget                     │  │
│             │  GET  /            ← Demo page                             │  │
│             │  CORS enabled      ← Cross-origin requests                │  │
│             └────────────────────────────────┬───────────────────────────┘  │
│                                              │                              │
│                                              ▼                              │
│                      ┌─────────────────────────────────┐                    │
│                      │  Chat Request Handler (main.py) │                    │
│                      │  - Extract user_id, message     │                    │
│                      │  - Store in session             │                    │
│                      │  - Route to intent handler      │                    │
│                      └──────────────┬──────────────────┘                    │
│                                     │                                       │
└─────────────────────────────────────┼───────────────────────────────────┬───┘
                                      │                                   │
                    ┌─────────────────┴────────────────┐                  │
                    │                                  │                  │
                    ▼                                  ▼                  ▼
┌──────────────────────────┐  ┌──────────────────────────┐  ┌───────────────┐
│  Intent Classification   │  │  Session Management      │  │  Storage      │
│  (intent.py)             │  │  (state.py)              │  │  (storage.py) │
├──────────────────────────┤  ├──────────────────────────┤  ├───────────────┤
│ Stage 1: Keyword Match   │  │ Session Structure:       │  │ File-based:   │
│  - GREETING              │  │ - created_at             │  │ ✓ sessions    │
│  - GRATITUDE             │  │ - history[]              │  │ ✓ interacts   │
│  - NAVIGATION            │  │ - collected_data         │  │ ✓ enquiries   │
│  - FAQ                   │  │ - current_flow           │  │ ✓ leads       │
│  - PROPERTY_SEARCH       │  │ - user_info              │  │               │
│  - GENERAL               │  │ - needs_classification   │  │ + Supabase:   │
│                          │  │ (TTL: 1 hour)            │  │ ✓ logging     │
│ Stage 2: Ollama LLM      │  │ Persistence: sessions.   │  │ ✓ querying    │
│ (fallback for complex)   │  │               json       │  │               │
│ Model: phi3:latest       │  │ Thread-safe (locks)      │  │ Thread-safe:  │
└────────────┬─────────────┘  └──────────┬───────────────┘  │ (per-file     │
             │                           │                  │  locks)       │
             └───────────────┬───────────┘                  │               │
                             │                              │               │
                             ▼                              ▼               │
┌─────────────────────────────────────────────────────────────────────────┤
│                    INTENT HANDLERS LAYER                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐     │
│  │ Property Search  │  │ FAQ Handler      │  │ Navigation       │     │
│  │ (property_       │  │ (faq_rag.py)     │  │ (navigation.py)  │     │
│  │  search.py)      │  ├──────────────────┤  ├──────────────────┤     │
│  ├──────────────────┤  │ Keyword Map:     │  │ Maps 20+ Routes: │     │
│  │ Parse Criteria:  │  │ - Home            │  │ - Homepage       │     │
│  │ - Budget (price) │  │ - Search          │  │ - Properties pg  │     │
│  │ - BHK (bedrooms) │  │ - Verification    │  │ - New projects   │     │
│  │ - City (location)│  │ - Charges         │  │ - City filter    │     │
│  │ - Type           │  │ - Loan            │  │ - Login/signup   │     │
│  │                  │  │ - Site visit      │  │ - Post prop      │     │
│  │ Query source:    │  │ - And more...     │  │ - Dashboard      │     │
│  │ 1. Supabase      │  │                  │  │ - Contact/FAQ    │     │
│  │ 2. properties.   │  │ LLM Fallback:     │  │                  │     │
│  │    json (backup) │  │ For complex Q     │  │ Base URL:        │     │
│  │                  │  │ (Ollama)          │  │ propertybrix.    │     │
│  │ Returns:         │  │                  │  │ com/en-new/      │     │
│  │ - Title          │  │ Returns:          │  │                  │     │
│  │ - Price          │  │ - Answer          │  │ Returns:         │     │
│  │ - Location       │  │ - FAQ_RESPONSE    │  │ - URL            │     │
│  │ - Bedrooms       │  │                  │  │ - Label          │     │
│  │ - Area           │  │                  │  │ - Message        │     │
│  │ - Status         │  │                  │  │                  │     │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘     │
│                                                                          │
│  ┌──────────────────────────┐  ┌──────────────────────────────────┐    │
│  │ Sales Funnel Handler     │  │ Greeting/General Handler         │    │
│  │ (in main.py)             │  │ (in main.py)                     │    │
│  ├──────────────────────────┤  ├──────────────────────────────────┤    │
│  │ 4-Step Flow:             │  │ Default responses for casual     │    │
│  │ 1. Purpose               │  │ interactions                     │    │
│  │ 2. Location              │  │                                  │    │
│  │ 3. Property Type         │  │ Examples:                        │    │
│  │ 4. Budget                │  │ - "Hi" → "Welcome!"              │    │
│  │                          │  │ - "Thanks" → "Happy to help!"    │    │
│  │ Collects missing field   │  │                                  │    │
│  │ Shows options buttons    │  │                                  │    │
│  │                          │  │                                  │    │
│  │ All collected →          │  │                                  │    │
│  │ Execute search           │  │                                  │    │
│  │ Return property results  │  │                                  │    │
│  └──────────────────────────┘  └──────────────────────────────────┘    │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                  BACKGROUND WORKER LAYER                                 │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │  Intent Classification Worker (async, runs every 30s)             │  │
│  ├────────────────────────────────────────────────────────────────────┤  │
│  │ 1. Check sessions idle > 60 seconds                               │  │
│  │ 2. Extract session data:                                          │  │
│  │    - Chat history (last 10 messages)                              │  │
│  │    - Pages visited                                                │  │
│  │    - Properties viewed count                                      │  │
│  │    - Time on site                                                 │  │
│  │ 3. Send to Ollama with prompt                                     │  │
│  │ 4. Parse response: HOT_LEAD | NORMAL_LEAD | NOT_A_LEAD            │  │
│  │ 5. If qualified (HOT or NORMAL):                                  │  │
│  │    - Save to leads.json                                           │  │
│  │    - Log to Supabase                                              │  │
│  │    - Mark session as classified                                   │  │
│  │                                                                    │  │
│  │ Purpose: Identify genuine buyers/renters for follow-up            │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                            │
└──────────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                   DATA PERSISTENCE LAYER                                 │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  LOCAL JSON FILES (backend/app/data/)                                    │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │ config.json        │ Company info, FAQs, cities, property types   │  │
│  │ properties.json    │ 400+ property listings (backup/fallback)     │  │
│  │ sessions.json      │ Active user sessions (persisted on disk)     │  │
│  │ interactions.json  │ Chat logs (last 1000, rotated)               │  │
│  │ enquiries.json     │ User property inquiries (pending follow-up)  │  │
│  │ leads.json         │ Qualified leads (HOT_LEAD, NORMAL_LEAD)      │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                            │
│  REMOTE DATABASE (Supabase - Optional)                                   │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │ conversations table    │ Chat messages (user_id, role, message)   │  │
│  │ properties table       │ Query properties (city, price, type)     │  │
│  │ enquiries table        │ Property inquiries                       │  │
│  │ leads table            │ Lead scores & classifications            │  │
│  │                                                                    │  │
│  │ Primary for: property lookup, lead logging                        │  │
│  │ Fallback: if down, continue with local JSON                       │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                            │
└──────────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                   EXTERNAL SERVICES LAYER                                │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  ┌─────────────────────────┐       ┌──────────────────────────────────┐  │
│  │ Ollama (LLM Engine)     │       │ Supabase (Database Backend)      │  │
│  ├─────────────────────────┤       ├──────────────────────────────────┤  │
│  │ URL: localhost:11434    │       │ Remote PostgreSQL database       │  │
│  │                         │       │                                  │  │
│  │ Model: phi3:latest      │       │ Features:                        │  │
│  │                         │       │ - Real-time queries              │  │
│  │ Used for:               │       │ - Automatic backups              │  │
│  │ 1. Complex NLU queries  │       │ - Row-level security             │  │
│  │ 2. Fallback intent      │       │ - API authentication             │  │
│  │ 3. Lead scoring         │       │                                  │  │
│  │ 4. FAQ LLM fallback     │       │ Optional integration             │  │
│  │                         │       │ (fallback to JSON works)         │  │
│  │ Response format: JSON   │       │                                  │  │
│  │ Timeout: 120s           │       │                                  │  │
│  │ Temperature: 0.0        │       │                                  │  │
│  │ (deterministic)         │       │                                  │  │
│  └─────────────────────────┘       └──────────────────────────────────┘  │
│                                                                            │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow - User Chat to Response

```
┌─────────────┐
│ User Types  │
│  "Hi there" │
└──────┬──────┘
       │ HTTP POST /chat
       │ {message, session_id, user}
       ▼
┌──────────────────────────────────────┐
│ FastAPI main.py - chat() endpoint    │
│ ✓ Validate request                   │
│ ✓ Extract session_id, message        │
│ ✓ Get/create user session            │
│ ✓ Log to history (clean msg)         │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│ intent.py - _keyword_classify()      │
│ Match against keyword sets:          │
│ - GREETING: "hi" ✓                   │
└──────────────┬───────────────────────┘
               │ Result: GREETING
               ▼
┌──────────────────────────────────────┐
│ Determine response type              │
│ intent=GREETING →                    │
│ Generate greeting message            │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│ Generate Response:                   │
│ {                                    │
│   "type": "text_response",           │
│   "message": "Hi! Welcome to...",    │
│   "options": [MENU_FIND,             │
│               MENU_FAQ, MENU_NAV]    │
│ }                                    │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│ Save interaction to storage          │
│ storage.py - append_interaction()    │
│ - Append to interactions.json        │
│ - Log to Supabase (async, safe)      │
│ - Keep last 1000 only                │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│ Return JSON Response to Frontend     │
│ ← 200 OK {response}                  │
└──────────────────────────────────────┘
       │
       ▼
   Browser renders + displays message
```

---

## Property Search Data Flow

```
User Query: "2BHK under 80L in Pune"
     │
     ▼
Intent Classification → PROPERTY_SEARCH
     │
     ▼
Property_search.py execution:
  _parse_price("under 80L")
    → (None, 0.80) in Crores
  
  _parse_bhk("2BHK")
    → bedrooms=2, type="apartment"
     │
     ▼
Query Supabase/JSON:
  WHERE city = "pune"
  AND type = "apartment"
  AND bedrooms = 2
  AND price <= 0.80
  LIMIT 10
     │
     ├─ Supabase DB ✓ (primary)
     │   ↓
     │   [Returns 8 results]
     │
     └─ properties.json (fallback)
         [If DB fails/empty]
     │
     ▼
Transform results to UI format:
  [{
    "title": "2 BHK in Vesu, Pune",
    "price": "₹72L",
    "location": "Vesu",
    "bedrooms": 2,
    "area_sqft": 1050,
    "url": "..."
  }, ...]
     │
     ▼
Return response:
  {
    "type": "property_results",
    "message": "I found 8 properties...",
    "results": [...]
  }
     │
     ▼
Frontend displays property cards
```

---

## Session Funnel Progress Tracking

```
Session Created (new_session())
│
├─ created_at: 1710854400
├─ history: []
├─ collected_data: {}
├─ current_flow: None
│
▼
User: "Want to buy property"
│
├─ Intent: PROPERTY_SEARCH
├─ current_flow: "property_search"
├─ collected_data: {}
│
▼
get_missing_sales_criteria() → "purpose"
│
├─ Display: "Great! Buy or Rent?"
├─ Options: [Buy, Rent, New Projects]
│
▼
User: "Buy Property"
│
├─ collected_data: {purpose: "Buy"}
├─ _run_funnel() checks again
│
▼
get_missing_sales_criteria() → "location"
│
├─ Display: "Which city?"
├─ Options: [Mumbai, Pune, Bangalore, ...]
│
▼
User: "Pune"
│
├─ collected_data: {purpose: "Buy", location: "Pune"}
│
▼
get_missing_sales_criteria() → "property_type"
│
├─ Display: "Property type?"
├─ Options: [1BHK, 2BHK, 3BHK, Villa, ...]
│
▼
User: "2 BHK"
│
├─ collected_data: {
│    purpose: "Buy",
│    location: "Pune",
│    property_type: "2 BHK"
│  }
│
▼
get_missing_sales_criteria() → "budget"
│
├─ Display: "Your budget?"
├─ Options: [₹30L-₹50L, ₹50L-₹80L, ₹80L-₹1Cr, ₹1Cr+]
│
▼
User: "BUDGET:50L-80L"
│
├─ collected_data: {
│    purpose: "Buy",
│    location: "Pune",
│    property_type: "2 BHK",
│    budget: "50L to 80L"
│  }
│
▼
get_missing_sales_criteria() → None (all collected!)
│
├─ Execute Property Search
├─ Return Results (8 properties)
├─ Reset: collected_data = {}
│
▼
Funnel Complete ✓
```

---

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   DEPLOYMENT OPTIONS                         │
└─────────────────────────────────────────────────────────────┘

LOCAL DEVELOPMENT:
┌─────────────────────────┐
│  make start             │
│  uvicorn + reload       │
│  Port 8001              │
│  http://localhost:8001  │
└─────────────────────────┘

PRODUCTION SERVER:
┌────────────────────────────────────────────┐
│  Docker Container (or Direct Install)      │
├────────────────────────────────────────────┤
│ ┌──────────────┐                          │
│ │ Gunicorn/    │ (ASGI server)            │
│ │ Uvicorn × 4  │ (4 worker processes)     │
│ │ workers      │                          │
│ └──────┬───────┘                          │
│        │ Port 8001                        │
│        ▼                                   │
│ ┌──────────────┐                          │
│ │ FastAPI App  │                          │
│ │ (main.py)    │                          │
│ └──────┬───────┘                          │
│        │                                   │
│ ┌──────▼──────────────────┐                │
│ │ Application Logic Layer │                │
│ │ (All modules)           │                │
│ └──────┬──────────────────┘                │
│        │                                   │
│ ┌──────▼─────────────────┐                 │
│ │ Data (JSON files)      │                 │
│ │ + External APIs        │                 │
│ └────────────────────────┘                 │
│                                             │
│  Requires:                                 │
│  - Python 3.8+                             │
│  - Ollama service (localhost:11434)        │
│  - Supabase (optional)                     │
│  - Env vars set                            │
└────────────────────────────────────────────┘

FRONTEND DEPLOYMENT:
┌────────────────────────────┐
│ 1. Static Hosting:         │
│    - demo.html             │
│    - login.html            │
│    - signup.html           │
├────────────────────────────┤
│ 2. Embeddable Widget:      │
│    - chatbot-embed.js      │
│    - Include in websites   │
├────────────────────────────┤
│ 3. Configuration Points:   │
│    window.CHATBOT_CONFIG   │
│    - apiUrl                │
│    - companyName           │
│    - primaryColor          │
└────────────────────────────┘
```

---

## Technology Stack Summary

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **API** | FastAPI 0.111 | Web framework |
| **Server** | Uvicorn 0.29 | ASGI application server |
| **LLM** | Ollama (local) | Intent classification & scoring |
| **Model** | Phi-3 | Lightweight language model (~4GB) |
| **Database** | Supabase (optional) | Cloud queries & logging |
| **Storage** | JSON files | Local persistence |
| **HTTP Client** | httpx 0.27 | Async requests to Ollama |
| **Validation** | Pydantic 2.7 | Data models & request validation |
| **Frontend** | HTML + JS | Demo + embeddable widget |
| **Styling** | CSS-in-JS | Responsive Material Design |

---

## Key Algorithms

### 1. Intent Classification (2-Stage)
```python
if keyword_match(message) != None:
    return keyword_match(message)  # GREETING, FAQ, etc.
else:
    return ollama_classify(message)  # Complex cases
```

### 2. Budget Parsing (Regex-based)
```
Input: "under 80 lakh" / "50L to 80L" / "above 1 crore"
↓
Regex extract: (number) (unit) [to (number) (unit)]
↓
Convert to Crores: L/Lakh → /100, Crore → ×1
↓
Return: (min_cr, max_cr) tuple
```

### 3. Session State Flow
```
get_session(id)
  ↓
if exists in memory: return + update last_active
if not exists: create new + save to disk
  ↓
Track collected_data for funnel
  ↓
Check if needs_classification
  ↓
expire after 1 hour inactivity
```

### 4. Lead Scoring (Background)
```
every 30 seconds:
  for each idle session (> 60s):
    analyze([chat_history, pages, properties_viewed, time])
    ↓
    call Ollama with structured prompt
    ↓
    parse: HOT_LEAD | NORMAL_LEAD | NOT_A_LEAD
    ↓
    if qualified: save to leads.json → Supabase
```

---

## Performance Characteristics

| Operation | Speed | Notes |
|-----------|-------|-------|
| Keyword intent match | <5ms | In-memory, regex-based |
| FAQ lookup | <10ms | Hash-map, no DB query |
| Navigation route | <5ms | String matching |
| JSON read/write | 10-50ms | File I/O, depends on size |
| Ollama LLM call | 1-5s | Remote service, async |
| Supabase query | 100-500ms | Network latency |
| Session lookup | <1ms | In-memory dict |
| Chat endpoint | 50-5000ms | Varies by intent |

---

## Security Considerations

- **Input Validation**: Pydantic models validate all requests
- **CORS**: Enabled for embeddable widget
- **Session ID**: Random 16-char identifiers
- **User Info**: Stored in encrypted Supabase (optional)
- **No Auth**: Currently assumes frontend handles auth
- **Rate Limiting**: Not implemented (add for production)
- **Data Cleanup**: Sessions auto-expire, old interactions rotated

---

## Monitoring & Observability

**Logs Generated**:
- Startup banner with version
- Intent classification results
- Property search queries & result counts
- Lead scoring outcomes
- Errors & exceptions

**Metrics Available**:
- Total chat messages processed
- Intent distribution
- Property search completion rate
- Lead conversion (HOT/NORMAL ratio)
- Session duration & activity
- API response times

**Files to Monitor**:
- `app/data/interactions.json` - Recent chats
- `app/data/leads.json` - Qualified leads
- `app/data/enquiries.json` - Property inquiries

---

## Scalability Notes

**Current Limitations**:
- Single-process (4 workers needed for production)
- In-memory session cache (restarts lose data)
- File-based locks (not suitable for distributed)
- JSON files (not indexed on large datasets)

**Improvements for Scale**:
1. Use Redis for session cache (replaces file)
2. Use PostgreSQL directly (replaces JSON files)
3. Use Kafka for event streaming (background jobs)
4. Implement proper rate limiting & load balancing
5. Add monitoring & alerting (Prometheus + Grafana)
6. Separate worker tasks from API processes

