# 🗓️ Multi-Agent Scheduling Assistant

A production-ready, multi-agent scheduling assistant built with **LangGraph**, **FastAPI**, and **React**. It orchestrates a **Triage Agent** (Groq) and a **Booking Specialist** (Google Gemini with Groq fallback) to handle natural-language calendar bookings, cancellations, rescheduling, and more — all backed by SQLite persistence and user authentication.

---

## ✨ Features

| Category | Details |
|---|---|
| **Multi-Agent Orchestration** | LangGraph `StateGraph` with conditional routing — a Triage Agent classifies intent, a Booking Specialist handles all scheduling operations. |
| **6 Booking Tools** | `check_availability`, `reserve_slot`, `list_bookings`, `cancel_slot`, `reschedule_slot`, `send_booking_notification`. |
| **Groq Fallback** | If Gemini hits a quota/rate-limit error, the Booking Specialist automatically retries with Groq (`llama-3.3-70b-versatile`) — zero user disruption. |
| **User Authentication** | Register / login / logout with PBKDF2-HMAC-SHA256 password hashing and Bearer token sessions. |
| **Per-User Thread Isolation** | Each authenticated user gets their own conversation threads, isolated bookings, and chat history. |
| **Chat History Sidebar** | Users can browse previous conversations and click to resume any thread. |
| **Date Normalization** | Resolves "tomorrow", "next Monday", "in 3 days" to absolute `YYYY-MM-DD` before tool calls. |
| **Slot Negotiation** | When a requested slot is taken, the agent proposes 2–3 alternative free slots. |
| **Webhook Notifications** | Users can paste a Webhook.site / Pipedream URL to receive booking confirmation POST requests. |
| **State Persistence** | LangGraph `SqliteSaver` checkpointer — conversation history survives page refreshes and server restarts. |
| **Cancel & Reschedule** | Users can cancel existing bookings or reschedule them to a new date/time atomically. |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (React + Vite)                │
│  ┌──────────┐  ┌──────────────┐  ┌────────────────────────┐ │
│  │ Login.jsx│  │ ChatWindow   │  │ Chat History Sidebar   │ │
│  │ Register │  │ ChatInput    │  │ (browse/resume threads)│ │
│  └────┬─────┘  └──────┬───────┘  └───────────┬────────────┘ │
│       │               │                      │              │
│       └───────────────┼──────────────────────┘              │
│                       │  fetch /api/*                        │
└───────────────────────┼─────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────┐
│                   Backend (FastAPI + LangGraph)               │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                    FastAPI App                        │    │
│  │  /api/register  /api/login  /api/logout  /api/health │    │
│  │  /api/thread    /api/threads  /api/chat  /api/history│    │
│  │  /api/test-webhook                                   │    │
│  └──────────────────────┬──────────────────────────────┘    │
│                         │                                    │
│  ┌──────────────────────▼──────────────────────────────┐    │
│  │              LangGraph StateGraph                    │    │
│  │                                                      │    │
│  │   START → [Triage Agent (Groq)]                      │    │
│  │              │                                       │    │
│  │              ├─ general query → respond → END        │    │
│  │              └─ booking intent → ROUTE_TO_BOOKING    │    │
│  │                                      │               │    │
│  │                   [Booking Specialist (Gemini+Groq)] │    │
│  │                   ├── check_availability             │    │
│  │                   ├── reserve_slot                   │    │
│  │                   ├── list_bookings                  │    │
│  │                   ├── cancel_slot                    │    │
│  │                   ├── reschedule_slot                │    │
│  │                   └── send_booking_notification      │    │
│  │                                      │               │    │
│  │                                   → END              │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────┐   │
│  │  Auth Module │  │   SQLite DB  │  │ SqliteSaver       │   │
│  │  (PBKDF2)   │  │  slots/users/ │  │ (conversation     │   │
│  │             │  │  sessions/    │  │  checkpoints)     │   │
│  │             │  │  user_threads │  │                   │   │
│  └─────────────┘  └──────────────┘  └───────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

### Agent Flow

1. **User sends a message** → FastAPI `/api/chat` endpoint receives it with a Bearer token.
2. **Auth middleware** validates the token, extracts `user_email`, and associates the thread with the user.
3. **LangGraph `StateGraph`** is invoked with the message, thread ID, user email, and optional webhook URL.
4. **Triage Agent (Groq `llama-3.3-70b-versatile`)** analyzes the message:
   - **General query** → responds directly (greeting, FAQ, small talk) → turn ends.
   - **Booking intent** → outputs `ROUTE_TO_BOOKING` token → routes to Booking Specialist.
5. **Booking Specialist (Gemini `gemini-2.5-flash` with Groq fallback)**:
   - Resolves relative dates to absolute `YYYY-MM-DD`.
   - Calls one or more of the 6 tools (check → reserve → notify, or list → cancel/reschedule).
   - Auto-injects the authenticated user's email into all email-requiring tools.
   - If Gemini fails (quota/rate-limit), automatically retries with Groq.
   - Loops up to 5 iterations for multi-step tool usage.
6. **Response** is returned to the frontend and displayed in the chat window.

---

## 📁 Project Structure

```
d:/ASSIGNMENT-2/
├── backend/                          # FastAPI + LangGraph backend
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                   # FastAPI app entry point + all REST endpoints
│   │   ├── config.py                 # Settings/env variable loading
│   │   ├── graph.py                  # LangGraph StateGraph definition + SqliteSaver
│   │   ├── state.py                  # BookingState TypedDict schema
│   │   ├── auth.py                   # PBKDF2 password hashing, sessions, FastAPI dependency
│   │   ├── db.py                     # SQLite layer: slots, users, sessions, threads, cancel, reschedule
│   │   ├── schemas.py                # Pydantic request/response models
│   │   ├── utils.py                  # Date normalization + validation helpers
│   │   ├── agents/
│   │   │   ├── __init__.py
│   │   │   ├── triage.py             # Triage Agent (Groq) — intent classification
│   │   │   └── booking.py            # Booking Specialist (Gemini + Groq fallback)
│   │   └── tools/
│   │       ├── __init__.py
│   │       ├── availability.py       # check_availability tool
│   │       ├── reserve.py            # reserve_slot tool
│   │       ├── list_bookings.py      # list_bookings tool
│   │       ├── cancel.py             # cancel_slot tool
│   │       ├── reschedule.py         # reschedule_slot tool
│   │       └── notify.py             # send_booking_notification tool (webhook)
│   ├── data/
│   │   └── app.db                    # SQLite database (auto-created on startup)
│   ├── .env                          # Environment variables (API keys, DB path, CORS)
│   ├── requirements.txt              # Python dependencies
│   ├── render.yaml                   # Render deployment blueprint
│   └── readme.md                     # Backend-specific documentation
├── frontend/                         # React + Vite frontend
│   ├── src/
│   │   ├── main.jsx                  # React entry point
│   │   ├── App.jsx                   # Main app: auth flow, chat, history sidebar
│   │   ├── api/
│   │   │   └── client.js             # API client (fetch wrapper with auth headers)
│   │   ├── components/
│   │   │   ├── Login.jsx             # Login/Register form
│   │   │   ├── ChatWindow.jsx        # Message display area
│   │   │   ├── ChatInput.jsx         # Message input box
│   │   │   ├── MessageBubble.jsx     # Individual message rendering
│   │   │   └── WebhookInput.jsx      # Webhook URL configuration
│   │   └── styles/
│   │       └── App.css               # All application styles
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   ├── vercel.json                   # Vercel deployment config
│   └── readme.md                     # Frontend-specific documentation
├── plan.md                           # Phased implementation plan
├── requirements.txt                  # Root-level Python requirements
├── pyproject.toml                    # Python project config
└── readme.md                         # This file
```

---

## 🚀 Local Development

### Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- **Groq API key** — get one at [console.groq.com](https://console.groq.com)
- **Google API key** — get one at [aistudio.google.com](https://aistudio.google.com)

### Backend Setup

```bash
cd backend

# Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
# Edit backend/.env:
#   GROQ_API_KEY="your_groq_key"
#   GOOGLE_API_KEY="your_google_key"
#   CORS_ORIGINS="http://localhost:5173"
#   DATABASE_URL="./data/app.db"

# Start the server
uvicorn app.main:app --reload --port 8000
```

The backend runs on `http://localhost:8000`. The database is auto-created at `backend/data/app.db` on first startup with seed data.

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Configure environment (optional — defaults to localhost:8000)
# Create frontend/.env.local:
#   VITE_API_URL=http://localhost:8000

# Start the dev server
npm run dev
```

The frontend runs on `http://localhost:5173`.

### Using the Application

1. Open `http://localhost:5173` in your browser.
2. **Register** a new account (email + password, min 6 chars).
3. Start chatting — try:
   - *"Book an appointment tomorrow at 2pm"*
   - *"Check availability for next Friday"*
   - *"Show me my bookings"*
   - *"Cancel my booking on 2026-07-15 at 14:00"*
   - *"Reschedule my appointment to next Monday at 10am"*
4. Optionally paste a **webhook URL** (from [webhook.site](https://webhook.site)) to receive booking notifications.
5. Click any **chat in the history sidebar** to resume a previous conversation.
6. Click **New Chat** to start a fresh conversation thread.

---

## 🔌 API Reference

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` | `/api/health` | No | Health check (for Render). |
| `POST` | `/api/register` | No | Register a new user. Body: `{email, password}`. Returns `{token, email}`. |
| `POST` | `/api/login` | No | Login existing user. Body: `{email, password}`. Returns `{token, email}`. |
| `POST` | `/api/logout` | Yes | Invalidate the current session token. |
| `POST` | `/api/thread` | Yes | Create a new conversation thread. Returns `{thread_id}`. |
| `GET` | `/api/threads` | Yes | List all thread IDs for the authenticated user. |
| `POST` | `/api/chat` | Yes | Send a message. Body: `{thread_id, message, webhook_url?}`. Returns `{reply, thread_id}`. |
| `GET` | `/api/history/{thread_id}` | Yes | Retrieve full conversation history for a thread. |
| `POST` | `/api/test-webhook` | Yes | Test a webhook URL with a sample payload. |

All authenticated endpoints require a `Authorization: Bearer <token>` header.

---

## 🛠️ Booking Tools

| Tool | Parameters | Description |
|------|-----------|-------------|
| `check_availability` | `date` | Returns free and taken time slots for a given date. |
| `reserve_slot` | `date`, `time`, `email` | Books a specific slot. Email is auto-injected from the authenticated user. |
| `list_bookings` | `email` | Lists all bookings for the user. Email is auto-injected. |
| `cancel_slot` | `date`, `time`, `email` | Cancels an existing booking. Verifies ownership. Email is auto-injected. |
| `reschedule_slot` | `old_date`, `old_time`, `new_date`, `new_time`, `email` | Atomically moves a booking to a new slot. Email is auto-injected. |
| `send_booking_notification` | `email`, `details`, `webhook_url` | Sends a POST request to the user's webhook with booking details. |

---

## 🗄️ Database Schema

The SQLite database (`backend/data/app.db`) contains four tables:

- **`slots`** — Booked appointments (`id`, `date`, `time`, `email`, `created_at`). Unique constraint on `(date, time)`.
- **`users`** — Registered users (`id`, `email`, `password_hash`, `salt`, `created_at`). Unique on `email`.
- **`sessions`** — Login sessions (`id`, `user_id`, `email`, `token`, `created_at`). Unique on `token`.
- **`user_threads`** — Maps threads to users (`id`, `user_email`, `thread_id`, `created_at`).

On startup, `init_db()` creates all tables and seeds 6 mock bookings if the `slots` table is empty.

---

## ☁️ Deployment

### Backend (Render)

1. Push the repository to GitHub.
2. Create a new **Web Service** on Render using `backend/render.yaml` (Blueprint).
3. Set environment variables:
   - `GROQ_API_KEY` — your Groq API key
   - `GOOGLE_API_KEY` — your Google API key
   - `CORS_ORIGINS` — your Vercel frontend URL (e.g. `https://your-app.vercel.app`)
   - `DATABASE_URL` — `./data/app.db` (default)
4. Render builds and deploys automatically. Health check: `/api/health`.

> **Note:** Render's free tier has an ephemeral filesystem — SQLite data resets on redeploy. For persistent storage, attach a Render Disk (paid) or use an external database.

### Frontend (Vercel)

1. Push the repository to GitHub.
2. Import the project on Vercel, setting the **root directory** to `frontend/`.
3. Set environment variable: `VITE_API_URL` = your Render backend URL.
4. Vercel builds and deploys automatically.

---

## 🔐 Security

- **Password hashing:** PBKDF2-HMAC-SHA256 with 100,000 iterations and per-user random salt.
- **Session tokens:** `secrets.token_urlsafe(32)` — cryptographically secure.
- **Per-user isolation:** Thread IDs are associated with user emails in `user_threads`. The `/api/threads` endpoint only returns threads belonging to the authenticated user.
- **Email auto-injection:** The authenticated user's email is injected server-side into all booking tools — users cannot book/cancel/reschedule on behalf of others.

---

## 🧰 Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend Framework** | FastAPI 0.115.6 |
| **Agent Orchestration** | LangGraph 0.2.60 |
| **Checkpointer** | langgraph-checkpoint-sqlite 2.0.1 |
| **LLM (Triage)** | Groq — `llama-3.3-70b-versatile` |
| **LLM (Booking)** | Google Gemini `gemini-2.5-flash` (primary) + Groq `llama-3.3-70b-versatile` (fallback) |
| **LangChain** | langchain-core 0.3.28, langchain-groq 0.2.2, langchain-google-genai 2.0.8 |
| **Database** | SQLite 3 |
| **Frontend** | React 18, Vite 6, react-markdown |
| **HTTP Client** | httpx 0.28.1 (backend), fetch (frontend) |
| **Deployment** | Render (backend), Vercel (frontend) |

---

## 📝 Environment Variables

### Backend (`backend/.env`)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GROQ_API_KEY` | Yes | — | Groq API key for Triage Agent + Booking fallback. |
| `GOOGLE_API_KEY` | Yes | — | Google API key for Gemini (Booking Specialist). |
| `CORS_ORIGINS` | No | `http://localhost:5173` | Comma-separated allowed CORS origins. |
| `DATABASE_URL` | No | `./data/app.db` | SQLite database file path. |

### Frontend (`frontend/.env.local`)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `VITE_API_URL` | No | `http://localhost:8000` | Backend API base URL. |

---

## 📜 License

This project is part of an academic assignment.
