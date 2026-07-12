# 🖥️ Frontend — Multi-Agent Scheduling Assistant UI

A **React + Vite** single-page application that provides a chat interface to the multi-agent scheduling assistant backend. Features user authentication, real-time chat, chat history sidebar, and webhook configuration.

---

## 🏗️ Architecture

```
frontend/src/
├── main.jsx              # React entry point
├── App.jsx               # Main app: auth flow, chat, history sidebar, state management
├── api/
│   └── client.js         # API client — fetch wrapper with auth token injection
├── components/
│   ├── Login.jsx         # Login/Register form (toggles between modes)
│   ├── ChatWindow.jsx    # Message display area (renders conversation)
│   ├── ChatInput.jsx     # Message input box (textarea + send button)
│   ├── MessageBubble.jsx # Individual message rendering (user vs assistant styling)
│   └── WebhookInput.jsx  # Webhook URL configuration field
└── styles/
    └── App.css           # All application styles
```

### Component Flow

```
App.jsx
  ├── (not authenticated) → Login.jsx
  │       └── register() / login() → onAuthSuccess()
  │
  └── (authenticated) → Chat layout
        ├── Sidebar
        │     ├── "New Chat" button → handleNewChat()
        │     ├── Chat History list → handleSelectThread(tid)
        │     └── User info + Logout button → handleLogout()
        │
        ├── ChatWindow.jsx (renders messages)
        │     └── MessageBubble.jsx (per message)
        │
        ├── WebhookInput.jsx (optional webhook URL)
        │
        └── ChatInput.jsx (message textarea)
              └── handleSend(text) → sendMessage() → updates messages
```

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| **Authentication** | Login and register forms with mode toggle. Bearer token stored in `localStorage`. |
| **Chat Interface** | Real-time message display with user/assistant message bubbles. Markdown rendering via `react-markdown`. |
| **Chat History Sidebar** | Lists all previous conversation threads for the authenticated user. Click any thread to resume it. Shows a preview (first user message, truncated to 50 chars). |
| **New Chat** | Creates a fresh conversation thread via `POST /api/thread`. |
| **Webhook Configuration** | Users can paste a Webhook.site / Pipedream URL to receive booking confirmation notifications. |
| **Thread Persistence** | Current thread ID and messages are stored in `localStorage` so the conversation survives page refreshes. |
| **Typing Indicator** | Animated "Assistant is typing..." indicator while waiting for a response. |
| **Responsive Design** | Sidebar + chat layout adapts to different screen sizes. |

---

## 🔌 API Client (`api/client.js`)

The API client wraps all backend calls and automatically injects the auth token.

| Function | Endpoint | Description |
|----------|----------|-------------|
| `register(email, password)` | `POST /api/register` | Register a new user. |
| `login(email, password)` | `POST /api/login` | Login existing user. |
| `logout()` | `POST /api/logout` | Invalidate session. |
| `createThread()` | `POST /api/thread` | Create a new conversation thread. |
| `getUserThreads()` | `GET /api/threads` | List user's thread IDs. |
| `sendMessage(threadId, message, webhookUrl)` | `POST /api/chat` | Send a message to the assistant. |
| `getHistory(threadId)` | `GET /api/history/{threadId}` | Get full conversation history. |
| `testWebhook(webhookUrl)` | `POST /api/test-webhook` | Test a webhook URL. |
| `setAuth(token, email)` | — | Store auth token + email in `localStorage`. |
| `clearAuth()` | — | Remove auth token from `localStorage`. |

**Auth handling:** `authHeaders()` automatically adds `Authorization: Bearer <token>` to all authenticated requests. Token and email are persisted in `localStorage` under keys `auth_token` and `auth_email`.

---

## 🚀 Running Locally

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

### Prerequisites

- **Node.js 18+**
- **Backend running** on `http://localhost:8000` (or set `VITE_API_URL`)

---

## 📦 Dependencies (`package.json`)

| Package | Version | Purpose |
|---------|---------|---------|
| `react` | ^18.3.1 | UI framework |
| `react-dom` | ^18.3.1 | React DOM renderer |
| `react-markdown` | ^9.0.1 | Render assistant responses as Markdown |
| `axios` | ^1.7.9 | HTTP client (available, fetch used in client.js) |

**Dev Dependencies:**

| Package | Version | Purpose |
|---------|---------|---------|
| `vite` | ^6.0.7 | Build tool + dev server |
| `@vitejs/plugin-react` | ^4.3.4 | React plugin for Vite |

---

## ⚙️ Configuration

### Environment Variables (`frontend/.env.local`)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `VITE_API_URL` | No | `http://localhost:8000` | Backend API base URL. |

### Vite Config (`vite.config.js`)

The Vite config sets up the React plugin and server options. The dev server runs on port 5173 by default.

---

## 🎨 Styling (`styles/App.css`)

All styles are in a single CSS file using modern CSS features:

- **CSS Grid / Flexbox** for layout (sidebar + chat area)
- **CSS custom properties** for theming (colors, spacing)
- **Animations** — `@keyframes fadeIn` for message appearance, `@keyframes typingBounce` for the typing indicator
- **Chat history sidebar** — scrollable thread list with hover/active states, preview text with ellipsis truncation
- **Message bubbles** — distinct styling for user (right-aligned) vs assistant (left-aligned) messages
- **Responsive** — adapts to different viewport sizes

---

## ☁️ Deployment (Vercel)

The `vercel.json` configures Vercel deployment:

- **Framework:** Vite
- **Build:** `npm run build`
- **Output:** `dist/`
- **Rewrites:** SPA fallback — all routes serve `index.html`

### Steps

1. Push the repository to GitHub.
2. Import the project on Vercel, setting the **root directory** to `frontend/`.
3. Set environment variable: `VITE_API_URL` = your backend URL (e.g. Render URL).
4. Vercel builds and deploys automatically.

---

## 🔐 Auth Flow

1. **Not authenticated** → `Login.jsx` is displayed with login/register toggle.
2. User enters email + password → `register()` or `login()` API call.
3. On success → `setAuth(token, email)` stores credentials in `localStorage`, `onAuthSuccess()` callback transitions to the chat view.
4. **Authenticated** → Chat interface with sidebar, chat window, and input.
5. All API calls automatically include the Bearer token via `authHeaders()`.
6. **Logout** → `logout()` API call + `clearAuth()` removes credentials → back to login screen.

---

## 💬 Chat Flow

1. **New chat** → `createThread()` → new `thread_id` stored in state + `localStorage`.
2. **Send message** → `sendMessage(threadId, text, webhookUrl)` → optimistic UI update (user message added immediately) → assistant response appended when API returns.
3. **Chat history** → `getUserThreads()` lists all thread IDs → for each, `getHistory(tid)` loads the first user message as a preview.
4. **Select thread** → `handleSelectThread(tid)` → `getHistory(tid)` loads full conversation → messages and thread ID set in state.
5. **Persistence** → Current `threadId` and `messages` are saved to `localStorage` so they survive page refreshes.
