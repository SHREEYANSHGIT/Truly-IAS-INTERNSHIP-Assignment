# 📹 Scheduling Assistant — 2-Minute Explanation Video Script

> **Total runtime:** ~2 minutes (120 seconds)
> **Pace:** ~140 words/minute | **Word count:** ~280 words
> **Tone:** Confident, technical, concise

---

## [0:00 – 0:15] Opening & Project Overview

**[Visual: Screen recording of the app — login screen, then chat interface]**

> This is an AI-powered Scheduling Assistant built with a multi-agent architecture. Users chat naturally to book, check, cancel, or reschedule appointments — and optionally receive booking confirmations via webhook.

---

## [0:15 – 0:35] Architecture Stack

**[Visual: Diagram showing React Frontend → FastAPI Backend → LangGraph → SQLite]**

> The stack has three layers. A **React frontend** with a glassmorphism UI and mobile-responsive drawer sidebar. A **FastAPI backend** exposing REST endpoints for auth, chat, and history. And a **LangGraph state machine** orchestrating two specialized AI agents.

---

## [0:35 – 1:05] The Multi-Agent Flow

**[Visual: Flow animation — User Message → Triage → Booking → Tools → Response]**

> Every message enters the **Triage Agent**, powered by Groq's Llama-3.3-70B. It classifies intent: general queries get answered directly, but any booking intent triggers the token `ROUTE_TO_BOOKING`, handing control to the **Booking Specialist**.

> The Booking Specialist uses **Google Gemini 2.5 Flash** with automatic **Groq fallback** — if Gemini hits a rate limit, it seamlessly retries on Groq so the user never sees an error. It has six tools: `check_availability`, `reserve_slot`, `list_bookings`, `cancel_slot`, `reschedule_slot`, and `send_booking_notification`.

---

## [1:05 – 1:30] State, Persistence & Smart Features

**[Visual: Code snippet of BookingState TypedDict + SqliteSaver checkpointer]**

> All agents share a `BookingState` TypedDict — conversation messages, user email, webhook URL, and pending booking. A **SqliteSaver checkpointer** persists every turn, so conversations survive restarts. The agent auto-injects the authenticated user's email into tool calls, resolves relative dates like "tomorrow" to absolute dates, and loops up to five times for multi-step tool chains like check → reserve → notify.

---

## [1:30 – 1:50] Webhook Confirmation & Mobile UI

**[Visual: Webhook input field → booking confirmation → webhook.site showing 200 OK, then mobile drawer toggle]**

> When a user configures a webhook URL, every successful booking triggers a POST with booking details to that endpoint. On the frontend, the UI is fully mobile-responsive — the sidebar collapses into a slide-in drawer with a hamburger toggle and backdrop overlay, using dynamic viewport height for proper mobile rendering.

---

## [1:50 – 2:00] Closing

**[Visual: Quick montage — booking flow, cancel, reschedule, webhook confirmation, mobile view]**

> Multi-agent orchestration, tool-calling LLMs with fallback resilience, persistent state, webhook notifications, and a responsive UI — all in one cohesive scheduling assistant.

---

## 📝 Production Notes

| Segment | Time | Visual Suggestion |
|---------|------|-------------------|
| Opening | 0:00–0:15 | Screen record: login → chat interface |
| Architecture | 0:15–0:35 | Animated diagram (React → API → LangGraph → SQLite) |
| Agent Flow | 0:35–1:05 | Flow chart: Triage → Booking → Tools → Response |
| State & Persistence | 1:05–1:30 | Code snippet of `BookingState` + `SqliteSaver` |
| Webhook & Mobile | 1:30–1:50 | Webhook test → webhook.site 200 OK, then mobile drawer |
| Closing | 1:50–2:00 | Fast montage of all features |

### Key Technical Terms to Emphasize
- **LangGraph** — state machine framework for multi-agent orchestration
- **Groq Llama-3.3-70B** — Triage Agent (fast classification)
- **Gemini 2.5 Flash** — Booking Specialist (tool-calling)
- **Groq fallback** — automatic resilience on rate limits
- **SqliteSaver** — conversation persistence across restarts
- **Tool-binding** — LLM autonomously calls booking tools
- **Webhook notification** — POST confirmation on successful booking
- **Mobile drawer** — responsive sidebar with hamburger toggle
