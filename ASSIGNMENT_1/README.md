# 🎧 GigaCorp Customer Support Assistant

A **Retrieval-Augmented Generation (RAG)** chatbot that answers customer-support
questions using the **GigaCorp Comprehensive FAQ** PDF. It runs locally with
Sentence Transformers embeddings, stores them in ChromaDB, and uses **Groq**
as the primary LLM with **Google Gemini** as an automatic fallback.

The interface is a modern, glassmorphic Streamlit chat UI with animated
backgrounds, source citations, conversation memory, and suggested questions.

---

## ✨ Features

| Feature | Details |
|---|---|
| **Modern Streamlit chat UI** | Glassmorphic design, animated background orbs, gradient hero header, typing indicator, custom avatars |
| **Suggested questions** | Clickable starter prompts on the empty state for instant onboarding |
| **PDF ingestion** | [`PyPDFLoader`](src/vectorstore.py) loads the FAQ and preserves page numbers |
| **Smart chunking** | [`RecursiveCharacterTextSplitter`](src/vectorstore.py) with 800-char chunks & 150 overlap |
| **Local embeddings** | [`sentence-transformers/all-MiniLM-L6-v2`](src/config.py) — no external API needed |
| **ChromaDB storage** | Embeddings persisted to disk; rebuilt only on first run |
| **Semantic retrieval** | Top-k similarity search returns the most relevant FAQ chunks |
| **Groq + Gemini fallback** | Groq is tried first; if unavailable, Gemini takes over transparently |
| **Conversation memory** | Sliding window of the last 6 turns for follow-up questions |
| **Source citations** | Every answer shows the page number and a text preview of the sources |
| **Dark theme** | Indigo/purple accent palette with Inter font and smooth animations |

---

## 📁 Project Structure

```
.
├── app.py                          # Streamlit entry point (UI + chat logic)
├── build_index.py                  # One-time ingestion script (pre-builds ChromaDB)
├── requirements.txt                # Python dependencies
├── .env.example                    # Template for API keys (no real keys)
├── .streamlit/
│   ├── config.toml                 # Streamlit server & theme config
│   └── secrets.toml.example        # Template for Streamlit Cloud secrets
├── data/
│   └── GigaCorp_Comprehensive_FAQ.pdf   # Source knowledge base
├── chroma_db/                      # Persisted vector store (committed, 135 vectors)
├── src/
│   ├── __init__.py
│   ├── config.py                   # Central configuration & env vars
│   ├── vectorstore.py              # PDF loading, chunking, embeddings, ChromaDB
│   ├── llm.py                      # Groq + Gemini LLM wrapper with fallback
│   └── memory.py                   # Short-term conversation memory (dependency-free)
└── README.md
```

---

## 🏗️ Architecture

```
User Question
     │
     ▼
┌─────────────────┐     ┌──────────────────┐
│  Streamlit UI   │────▶│  Retrieve top-k  │
│  (app.py)       │     │  chunks (Chroma) │
└─────────────────┘     └────────┬─────────┘
                                 │
                                 ▼
                    ┌────────────────────────┐
                    │  Format context +      │
                    │  conversation memory   │
                    └────────┬───────────────┘
                             │
                             ▼
               ┌─────────────────────────────┐
               │  LLM (Groq → Gemini fallback)│
               └─────────────┬───────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  Answer +       │
                    │  Source citations│
                    └─────────────────┘
```

### RAG Pipeline

1. **Ingestion** ([`build_vectorstore()`](src/vectorstore.py)): The FAQ PDF is
   loaded with `PyPDFLoader`, split into 800-character chunks (150 overlap),
   embedded with `all-MiniLM-L6-v2`, and stored in ChromaDB. This runs once;
   the persisted `chroma_db/` directory is committed to the repo.

2. **Retrieval** ([`retrieve()`](src/vectorstore.py)): On each user query,
   the top-4 most similar chunks are fetched via ChromaDB similarity search.

3. **Generation** ([`answer_query()`](src/llm.py)): The retrieved context +
   conversation history are passed to the LLM with a system prompt that
   instructs it to answer only from the FAQ and cite page numbers.

4. **Fallback** ([`get_llm()`](src/llm.py)): Groq is initialized first. If the
   Groq API key is missing or initialization fails, Gemini is used instead.

5. **Memory** ([`ConversationMemory`](src/memory.py)): A lightweight
   dependency-free sliding window keeps the last 6 turns so follow-up
   questions like "How much does it cost to ship *there*?" resolve correctly.

---

## 🚀 Quick Start (Local)

### 1 · Clone & install

```bash
git clone <your-repo-url>
cd <repo-name>
pip install -r requirements.txt
```

### 2 · Configure API keys

Copy the example env file and fill in your keys:

```bash
cp .env.example .env
```

```ini
GROQ_API_KEY=your_groq_api_key_here
GOOGLE_API_KEY=your_google_api_key_here
```

> **Where to get keys**
> - Groq: <https://console.groq.com/keys>
> - Google Gemini: <https://aistudio.google.com/apikey>

At least one key is required. If only one is provided, that provider is used
exclusively.

### 3 · Run the app

```bash
streamlit run app.py
```

The app will automatically:
1. Load the persisted ChromaDB from `chroma_db/` (no re-embedding needed).
2. Initialize the LLM provider (Groq primary, Gemini fallback).
3. Launch the chat interface at `http://localhost:8501`.

> **Note**: The `chroma_db/` directory is committed to the repo with 135
> pre-computed vectors, so the app works immediately without re-running
> the embedding pipeline.

---

## ☁️ Deploy on Streamlit Community Cloud

1. **Push to GitHub** — make sure your repo is public. Verify that `.env`
   and `.streamlit/secrets.toml` are **not** committed (they're in
   [`.gitignore`](.gitignore)).

2. **Add secrets** — go to your app settings on
   <https://share.streamlit.io> → **Secrets** and add:

   ```toml
   GROQ_API_KEY = "your_groq_api_key"
   GOOGLE_API_KEY = "your_google_api_key"
   ```

   > The app reads from both `.env` (local) and Streamlit secrets (cloud)
   > automatically via [`python-dotenv`](src/config.py) and `st.secrets`.

3. **Deploy** — click **New app** on Streamlit Cloud, select your repo, set the
   main file to `app.py`, and deploy.

4. **First-run note** — the initial deployment loads the persisted ChromaDB
   from disk (committed in the repo), so no re-embedding is needed.
   Subsequent restarts are instant.

---

## 🧪 Testing the Application

Once the app is running (locally or deployed), test it with these scenarios:

### Basic Q&A
1. Type: **"Do you ship internationally?"**
   - ✅ Expected: Answer about shipping zones with a source citation (page number).

### Conversation Memory (Follow-up)
1. Type: **"Do you ship to India?"**
   - ✅ Expected: Answer citing Zone 4 shipping rate.
2. Type: **"How much does it cost to ship there?"**
   - ✅ Expected: The assistant resolves "there" = India using memory and
     answers with the India-specific rate.

### Source Citations
- Every assistant reply includes a **📚 Sources & Citations** expander.
- Click it to see source cards with page numbers and text previews.

### Suggested Questions
- On first load (empty chat), click any of the 4 suggestion cards to
  instantly ask a common question.

### Provider Fallback
- If only `GROQ_API_KEY` is set → Groq is used (shown in sidebar).
- If only `GOOGLE_API_KEY` is set → Gemini is used.
- If both are set → Groq is primary, Gemini is fallback.

---

## 🔧 Configuration

All settings live in [`src/config.py`](src/config.py) and can be overridden via
environment variables:

| Setting | Default | Description |
|---|---|---|
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | HuggingFace embedding model |
| `CHUNK_SIZE` | `800` | Max characters per chunk |
| `CHUNK_OVERLAP` | `150` | Overlap between chunks |
| `RETRIEVAL_K` | `4` | Number of chunks retrieved per query |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Groq model name |
| `GEMINI_MODEL` | `gemini-1.5-flash` | Gemini model name |
| `MEMORY_K` | `6` | Conversation turns kept in memory |

---

## 🔒 Security

- **API keys are never committed** — `.env` and `.streamlit/secrets.toml` are
  in [`.gitignore`](.gitignore).
- [`.env.example`](.env.example) and
  [`.streamlit/secrets.toml.example`](.streamlit/secrets.toml.example) contain
  only placeholder values.
- On Streamlit Cloud, keys are injected via the encrypted secrets manager.

---

## 🛠️ Tech Stack

| Component | Technology |
|---|---|
| **UI** | Streamlit (dark theme, custom CSS) |
| **Framework** | LangChain |
| **Embeddings** | Sentence Transformers (`all-MiniLM-L6-v2`) |
| **Vector Store** | ChromaDB (persisted to disk) |
| **LLM (primary)** | Groq (`llama-3.3-70b-versatile`) |
| **LLM (fallback)** | Google Gemini (`gemini-1.5-flash`) |
| **PDF Parsing** | PyPDF |
| **Memory** | Custom sliding-window buffer |

---

## 📝 License

This project is provided for educational purposes.
