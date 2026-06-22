# 🚀 Property Brix AI Chatbot (v2.0.0)

A next-generation, FastAPI-powered real estate assistant designed to bridge the gap between casual browsing and hot sales conversions. 

Unlike standard "dumb" FAQ widgets or bloated general-purpose LLM wrappers, the **Property Brix AI Chatbot** is built specifically for high-intent real estate lead generation using a hybrid architecture.

---

## 🌟 What Makes This Chatbot Different? (Specialities)

### 1. ⚡ Hybrid Intent Engine: Zero-Latency + Intelligent Fallbacks
* **The Problem with LLMs:** Running everything through LLMs is slow, expensive, and prone to hallucination.
* **Our Solution:** A **two-stage intent classifier**:
  * **Stage 1 (Instant):** Fast regex and keyword mapping routes common inputs (Greetings, Gratitude, Navigation queries, standard FAQs) instantly.
  * **Stage 2 (Fallback):** Transparent fallback to a local **Ollama LLM** (`phi3:latest`) only when complex natural language requires semantic understanding.

### 2. 🎯 Background Lead Scoring & Classification
* Most chatbots wait for users to fill out contact forms. This chatbot **actively hunts for leads in the background**.
* A background thread evaluates idle sessions after 60 seconds of inactivity using local LLM-driven heuristics to classify them into:
  * **🔥 HOT_LEAD**: Actively specified criteria, high intent (e.g. asking to visit, price talks, specific BHK in specific city).
  * **NORMAL_LEAD**: Successfully completed the property search funnel.
  * **NOT_A_LEAD**: Casual browsing, general support FAQs.
* These are logged automatically to both local memory and remote databases for immediate sales follow-up.

### 3. 🔍 Guided Search Funnel + Flexible Natural Language Parsing
* Guided property search guides the user step-by-step: `Purpose` ➔ `Location` ➔ `Property Type` ➔ `Budget`.
* Supports robust natural language parsing. If a user types *"I want a 2 BHK in Pune under 80 lakh"*, the chatbot extracts the parameters directly, short-circuits the funnel, and shows property matches instantly.

### 4. 🔒 Resilient Fail-Safe Architecture
* **Dual Database Fallback:** Connects to **Supabase** for real-time querying, remote conversation logging, and enquiries. If the remote database goes offline, it automatically falls back to local JSON databases without interrupting the user experience.
* **Thread-Safe local storage:** Implements file locks on critical local data resources (`sessions.json`, `leads.json`, `enquiries.json`) to prevent data corruption.
* **State Persistence:** Session states persist to disk, meaning the chatbot remembers user context, search criteria, and chat history even if the backend server restarts.

---

## 🏗️ Project Architecture

```
propertybrix-chatbot/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI app, chat endpoints, lead worker
│   │   ├── intent.py               # Two-stage intent classifier
│   │   ├── intent_classifier.py    # Lead qualification & scoring engine
│   │   ├── property_search.py      # Property search parser & query builder
│   │   ├── faq_rag.py              # Zero-latency FAQ lookup
│   │   ├── navigation.py           # Deep-link navigator for 20+ routes
│   │   ├── state.py                # Stateful session & funnel manager
│   │   ├── storage.py              # Thread-safe JSON persistence layer
│   │   ├── supabase_service.py     # Remote database operations
│   │   └── data/                   # Fallback databases & configuration
│   │       ├── config.json         # FAQ lists, cities, & metadata
│   │       ├── properties.json     # 400+ local property catalog fallback
│   │       └── ...
│   └── requirements.txt            # Python dependencies
├── frontend/
│   ├── chatbot-embed.js            # Lightweight embeddable chat widget JS
│   └── demo.html                   # Interactive playground demonstrating the widget
├── Makefile                        # Development automation (venv, install, start)
└── test_*.py                       # Unit and integration test suite
```

---

## 🛠️ Getting Started

### Prerequisites
* Python 3.8+
* [Ollama](https://ollama.com/) (Required for LLM fallbacks and background lead scoring)
  ```bash
  ollama pull phi3:latest
  ```

### Quick Start
1. **Prepare Virtual Environment & Install Dependencies**:
   ```bash
   make venv
   make install
   ```
2. **Configure Environment**:
   Create a `.env` in the `backend/` directory:
   ```env
   OLLAMA_BASE_URL=http://localhost:11434
   LLM_MODEL=phi3:latest
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_KEY=your-anon-key
   ```
3. **Start the Application**:
   ```bash
   make start
   ```

---

## 🔌 Integrating the Chat Widget

Add the following configuration and script tags to the bottom of your HTML pages:

```html
<script>
  window.CHATBOT_CONFIG = { 
    apiUrl: "http://localhost:8001",
    companyName: "Property Brix",
    primaryColor: "#10B981" // Custom UI accent color
  };
</script>
<script src="http://localhost:8001/widget.js" defer></script>
```

---

## 🧪 Testing

Run tests to verify intent classification, API routing, search logic, and lead generation:
```bash
python test_all.py
```
