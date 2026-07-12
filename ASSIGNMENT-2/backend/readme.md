# 📦 Backend — Multi-Agent Scheduling Assistant API

The backend is a **FastAPI** application that exposes a LangGraph-powered multi-agent scheduling workflow over a REST API. It features user authentication, SQLite persistence, conversation checkpointing, and six booking tools (check, reserve, list, cancel, reschedule, notify).

---

## 🏗️ Architecture

```
backend/app/
├── main.py          # FastAPI app — all REST endpoints + startup
├── config.py        # Settings (env vars: API keys, CORS, DB path)
├── graph.py         # LangGraph StateGraph + SqliteSaver checkpointer
├── state.py         # BookingState TypedDict (shared graph state)
├── auth.py          # PBKDF2 hashing, session tokens, FastAPI dependency
├── db.py            # SQLite layer (slots, users, sessions, threads, cancel, reschedule)
├── schemas.py       # Pydantic request/response models
├── utils.py         # Date normalization + validation helpers
├── agents/
│   ├── triage.py    # Triage Agent (Groq llama-3.3-70b-versatile)
│   └── booking.py   # Booking Specialist (Gemini + Groq fallback)
└── tools/
    ├── availability.py   # check_availability
    ├── reserve.py        # reserve_slot
    ├── list_bookings.py  # list_bookings
    ├── cancel.py         # cancel_slot
    ├── reschedule.py     # reschedule_slot
    └── notify.py         # send_booking_notification (webhook)
```

### Request Flow

```
HTTP Request → FastAPI endpoint → Auth middleware (Bearer token)
  → LangGraph StateGraph invoked
    → Triage Agent (Groq) classifies intent
      → general query → direct response → END
      → booking intent → ROUTE_TO_BOOKING
        → Booking Specialist (Gemini, Groq fallback)
          → resolves relative dates
          → calls tools (check → reserve → notify, or list → cancel/reschedule)
          → auto-injects user email
          → loops up to 5 iterations
        → END
  → Response returned to client
```

---

## 🔌 API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/api/health` | No | Health check — returns `{"status":"ok"}`. |
| `POST` | `/api/register` | No | Register new user. Body: `{"email","password"}`. Returns `{"token","email"}`. |
| `POST` | `/api/login` | No | Login. Body: `{"email","password"}`. Returns `{"token","email"}`. |
| `POST` | `/api/logout` | Yes | Invalidate session token. Returns `{"success":true}`. |
| `POST` | `/api/thread` | Yes | Create a new conversation thread. Returns `{"thread_id"}`. |
| `GET` | `/api/threads` | Yes | List all thread IDs for the authenticated user. |
| `POST` | `/api/chat` | Yes | Send a message. Body: `{"thread_id","message","webhook_url?"}`. Returns `{"reply","thread_id"}`. |
| `GET` | `/api/history/{thread_id}` | Yes | Get full conversation history for a thread. |
| `POST` | `/api/test-webhook` | Yes | Test a webhook URL with a sample payload. |

**Auth:** All `Yes` endpoints require `Authorization: Bearer <token>` header.

**Interactive docs:** Visit `http://localhost:8000/docs` for Swagger UI.

---

## 🤖 Agents

### Triage Agent (`agents/triage.py`)

- **Model:** Groq `llama-3.3-70b-versatile` (temperature 0.2)
- **Role:** Classifies user intent — general query vs. booking intent.
- **Routing:** If booking intent detected, outputs `ROUTE_TO_BOOKING` token and hands off to the Booking Specialist. Otherwise responds directly.

### Booking Specialist (`agents/booking.py`)

- **Primary Model:** Google Gemini `gemini-2.5-flash` (temperature 0.3)
- **Fallback Model:** Groq `llama-3.3-70b-versatile` (temperature 0.3)
- **Fallback Logic:** `_invoke_with_fallback()` tries Gemini first. On any exception (quota, rate limit, network), it logs a warning and retries the same messages with Groq — zero user disruption.
- **Tool Binding:** Both Gemini and Groq LLMs are bound to all 6 tools via `bind_tools()`.
- **Date Pre-processing:** `_extract_relative_dates()` resolves "tomorrow", "next Monday", "in 3 days" to absolute `YYYY-MM-DD` before the LLM sees the message.
- **Tool Execution Loop:** `_handle_tool_calls()` executes tool calls inline and re-invokes the model, looping up to 5 times for multi-step workflows (check → reserve → notify, or list → cancel/reschedule).
- **Email Auto-Injection:** The authenticated user's email is automatically injected into `reserve_slot`, `list_bookings`, `cancel_slot`, and `reschedule_slot` tool calls.

---

## 🛠️ Tools

| Tool | File | Parameters | Description |
|------|------|-----------|-------------|
| `check_availability` | `tools/availability.py` | `date` | Returns free/taken slots for a date. |
| `reserve_slot` | `tools/reserve.py` | `date`, `time`, `email` | Books a slot. Validates date/time/email, double-checks availability. |
| `list_bookings` | `tools/list_bookings.py` | `email` | Lists all bookings for an email, sorted by date/time. |
| `cancel_slot` | `tools/cancel.py` | `date`, `time`, `email` | Cancels a booking. Verifies ownership before deleting. |
| `reschedule_slot` | `tools/reschedule.py` | `old_date`, `old_time`, `new_date`, `new_time`, `email` | Atomically moves a booking. Rolls back if the new slot is taken. |
| `send_booking_notification` | `tools/notify.py` | `email`, `details`, `webhook_url` | POSTs booking details to a webhook. Mock mode if no URL. |

All tools use the `@tool` decorator from `langchain_core.tools`.

---

## 🗄️ Database Layer (`db.py`)

### Tables

| Table | Columns | Notes |
|-------|---------|-------|
| `slots` | `id`, `date`, `time`, `email`, `created_at` | `UNIQUE(date, time)`. Seeded with 6 mock bookings on init. |
| `users` | `id`, `email`, `password_hash`, `salt`, `created_at` | `UNIQUE(email)`. |
| `sessions` | `id`, `user_id`, `email`, `token`, `created_at` | `UNIQUE(token)`. |
| `user_threads` | `id`, `user_email`, `thread_id`, `created_at` | Maps threads to users. |

### Key Functions

- `init_db()` — Creates all tables + seeds mock data. Called on FastAPI startup.
- `create_user()` / `get_user_by_email()` — User registration/lookup.
- `create_session()` / `get_session()` / `delete_session()` — Session management.
- `save_user_thread()` / `get_user_threads()` — Thread-user association.
- `get_taken_slots()` / `get_free_slots()` / `is_slot_available()` / `insert_slot()` — Slot operations.
- `cancel_slot(date, time, email)` — Verifies ownership, deletes the booking.
- `reschedule_slot(old_date, old_time, new_date, new_time, email)` — Verifies old booking, checks new slot availability, deletes old + inserts new atomically with rollback on `IntegrityError`.
- `get_all_slots()` — Returns all bookings (used by `list_bookings`).

All database operations are thread-safe via a module-level `threading.Lock`.

---

## 🔐 Authentication (`auth.py`)

- **Password Hashing:** PBKDF2-HMAC-SHA256, 100,000 iterations, per-user 16-byte random salt (`secrets.token_hex(16)`).
- **Session Tokens:** `secrets.token_urlsafe(32)` — 43-character URL-safe tokens.
- **FastAPI Dependency:** `get_current_user()` extracts and validates the Bearer token from the `Authorization` header via `HTTPBearer`.
- **Validation:** Email must contain `@`, password must be ≥ 6 characters.

---

## ⚙️ Configuration (`config.py`)

Settings are loaded from `backend/.env` via `python-dotenv` and cached with `lru_cache`.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GROQ_API_KEY` | Yes | — | Groq API key. |
| `GOOGLE_API_KEY` | Yes | — | Google Gemini API key. |
| `CORS_ORIGINS` | No | `http://localhost:5173` | Comma-separated allowed origins. |
| `DATABASE_URL` | No | `./data/app.db` | SQLite file path. |

---

## 🚀 Running Locally

```bash
cd backend

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Configure .env (see Configuration above)

# Start the server
uvicorn app.main:app --reload --port 8000
```

The server runs on `http://localhost:8000`. Swagger docs at `/docs`.

The SQLite database is auto-created at `backend/data/app.db` on first startup.

---

## 📦 Dependencies (`requirements.txt`)

| Package | Version | Purpose |
|---------|---------|---------|
| `fastapi` | 0.115.6 | Web framework |
| `uvicorn[standard]` | 0.34.0 | ASGI server |
| `langgraph` | 0.2.60 | Agent orchestration |
| `langgraph-checkpoint-sqlite` | 2.0.1 | Conversation persistence |
| `langchain-core` | 0.3.28 | LangChain core (tools, messages) |
| `langchain-groq` | 0.2.2 | Groq LLM integration |
| `langchain-google-genai` | 2.0.8 | Google Gemini integration |
| `pydantic` | 2.10.4 | Data validation |
| `pydantic-settings` | 2.7.1 | Settings management |
| `python-dotenv` | 1.0.1 | .env loading |
| `httpx` | 0.28.1 | HTTP client (webhook notifications) |
| `python-dateutil` | 2.9.0 | Date parsing utilities |

---

## ☁️ Deployment (Render)

The `render.yaml` blueprint defines a Python web service:

- **Runtime:** Python
- **Build:** `pip install -r requirements.txt`
- **Start:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Health Check:** `/api/health`
- **Env Vars:** `GROQ_API_KEY`, `GOOGLE_API_KEY`, `CORS_ORIGINS`, `DATABASE_URL`

> **Note:** Render's free tier has an ephemeral filesystem. SQLite data resets on redeploy. For persistent storage, attach a Render Disk (paid) or use an external database.

---

## 🔄 Resetting the Database

To start with a fresh database:

1. Stop the server.
2. Delete `backend/data/app.db` (and `app.db-wal`, `app.db-shm` if present).
3. Restart the server — `init_db()` recreates all tables and seeds mock data automatically.
