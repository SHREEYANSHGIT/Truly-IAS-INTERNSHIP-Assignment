# 🚀 Deployment Guide — Render (Backend) + Vercel (Frontend)

This guide deploys the **Scheduling Assistant** to free-tier hosting:

| Component | Platform | Free Tier |
|-----------|----------|-----------|
| FastAPI Backend | [Render](https://render.com) | Free Web Service (spins down after 15 min idle) |
| React Frontend | [Vercel](https://vercel.com) | Hobby plan (always on) |

---

## Prerequisites

1. A GitHub repository with this project pushed to it
2. Accounts on [Render](https://render.com) and [Vercel](https://vercel.com)
3. API keys ready:
   - **Groq API Key** → [console.groq.com/keys](https://console.groq.com/keys)
   - **Google Gemini API Key** → [aistudio.google.com/apikey](https://aistudio.google.com/apikey)

---

## Step 1 — Deploy Backend to Render

### 1.1 Create a New Web Service

1. Go to [dashboard.render.com](https://dashboard.render.com) → **New +** → **Web Service**
2. Connect your GitHub repository
3. Configure the service:

| Setting | Value |
|--------|-------|
| **Name** | `scheduling-assistant-api` |
| **Runtime** | Python 3 |
| **Root Directory** | `backend` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `gunicorn app.main:app -w 1 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT --timeout 120` |
| **Instance Type** | Free |

> 💡 Alternatively, use the **Render Blueprint** feature: go to
> **New +** → **Blueprint**, select your repo, and Render will auto-detect
> `backend/render.yaml` and configure everything for you.

### 1.2 Set Environment Variables

In the Render dashboard → **Environment** tab, add these variables:

| Key | Value | Notes |
|-----|-------|-------|
| `GROQ_API_KEY` | `gsk_your_groq_key` | Get from Groq Console |
| `GOOGLE_API_KEY` | `AIza_your_gemini_key` | Get from Google AI Studio |
| `CORS_ORIGINS` | `https://your-app.vercel.app` | Set AFTER Step 2 (your Vercel URL) |
| `DATABASE_URL` | `./data/app.db` | Already set in render.yaml |

> ⚠️ **Important:** The `CORS_ORIGINS` value must match your Vercel frontend URL
> exactly (including `https://` and no trailing slash). Update it after you
> complete Step 2 and know your Vercel domain.

### 1.3 Deploy

1. Click **Create Web Service**
2. Wait for the build to complete (~2-3 minutes)
3. Note your backend URL, e.g.: `https://scheduling-assistant-api.onrender.com`
4. Test the health endpoint: `https://your-backend-url.onrender.com/api/health`
   Should return: `{"status":"ok","service":"scheduling-assistant-api"}`

---

## Step 2 — Deploy Frontend to Vercel

### 2.1 Create a New Project

1. Go to [vercel.com](https://vercel.com) → **Add New** → **Project**
2. Import your GitHub repository
3. Configure the project:

| Setting | Value |
|--------|-------|
| **Framework Preset** | Vite |
| **Root Directory** | `frontend` |
| **Build Command** | `npm run build` |
| **Output Directory** | `dist` |
| **Install Command** | `npm install` |

> Vercel will auto-detect `frontend/vercel.json` and apply the SPA rewrites.

### 2.2 Set Environment Variables

In the Vercel project → **Settings** → **Environment Variables**, add:

| Key | Value |
|-----|-------|
| `VITE_API_URL` | `https://scheduling-assistant-api.onrender.com` |

> Replace with your actual Render backend URL from Step 1.3.
> No trailing slash.

### 2.3 Deploy

1. Click **Deploy**
2. Wait for the build (~1 minute)
3. Note your frontend URL, e.g.: `https://scheduling-assistant.vercel.app`

---

## Step 3 — Connect the Two (CORS)

1. Go back to your **Render** dashboard → **Environment**
2. Update `CORS_ORIGINS` to your Vercel URL:
   ```
   https://scheduling-assistant.vercel.app
   ```
3. Save changes — Render will auto-redeploy

---

## Step 4 — Verify

1. Visit your Vercel frontend URL
2. Register a new account
3. Send a chat message (e.g., "Book a meeting tomorrow at 3pm")
4. The assistant should respond and book the slot
5. Optionally configure a webhook URL (e.g., from [webhook.site](https://webhook.site))
   and verify booking confirmations are POSTed

---

## ⚠️ Render Free Tier Limitations

| Limitation | Impact | Mitigation |
|------------|--------|------------|
| **Spins down after 15 min idle** | First request after idle takes ~30-50s to wake | Acceptable for demo; upgrade to paid for production |
| **512 MB RAM** | Sufficient for this app | — |
| **Shared CPU** | Slower response times | Acceptable for demo |
| **SQLite is ephemeral** | Database resets on redeploy/sleep | Data persists during uptime; for production use PostgreSQL |

> 💡 The SQLite database lives at `./data/app.db` inside the container.
> It persists across requests but **resets on redeploy or spin-down**.
> This is fine for a demo. For production, attach a managed PostgreSQL database
> and update `DATABASE_URL`.

---

## 🔧 Local Development

### Backend
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux
pip install -r requirements.txt

# Create backend/.env with:
#   GROQ_API_KEY=gsk_...
#   GOOGLE_API_KEY=AIza...
#   CORS_ORIGINS=http://localhost:5173
#   DATABASE_URL=./data/app.db

uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
# Vite dev server proxies /api to localhost:8000 automatically
```

---

## 📁 Deployment File Reference

| File | Purpose |
|------|---------|
| [`backend/render.yaml`](backend/render.yaml) | Render Blueprint config (auto-detected by Render) |
| [`backend/requirements.txt`](backend/requirements.txt) | Python dependencies (includes gunicorn for production) |
| [`backend/.python-version`](backend/.python-version) | Pins Python 3.12.3 for Render |
| [`frontend/vercel.json`](frontend/vercel.json) | Vercel config (Vite framework, SPA rewrites, asset caching) |
| [`frontend/.env.example`](frontend/.env.example) | Template for `VITE_API_URL` env var |
| [`frontend/vite.config.js`](frontend/vite.config.js) | Vite config with dev proxy to backend |

---

## 🆘 Troubleshooting

### CORS errors in browser console
- Ensure `CORS_ORIGINS` on Render matches your Vercel URL **exactly** (https, no trailing slash)
- Redeploy the backend after changing env vars

### Frontend can't reach backend
- Verify `VITE_API_URL` is set in Vercel env vars (not just `.env.local`)
- Redeploy the frontend after adding env vars
- Check the backend health endpoint responds: `https://your-backend.onrender.com/api/health`

### Backend returns 502/503 on first request
- Render free tier spins down after 15 min idle — the first request wakes it up (~30s)
- Subsequent requests are fast

### Gemini API 429 quota errors
- The free tier has a daily request limit
- The app automatically falls back to Groq (Llama-3.3-70B) when Gemini rate-limits
- This is expected behavior — check server logs for "Falling back to Groq"

### Database resets after redeploy
- Render free tier has ephemeral disk storage
- This is expected — SQLite data (users, bookings) resets on each deploy
- For persistent data, upgrade to a paid plan or use an external database
