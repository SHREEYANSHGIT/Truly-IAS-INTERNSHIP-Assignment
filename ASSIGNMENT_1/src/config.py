"""Central configuration for the GigaCorp support chatbot.

All tunable settings (paths, model names, retrieval parameters) live here so the
rest of the codebase can import a single source of truth.
"""

from __future__ import annotations

import os
from pathlib import Path

# Prevent Transformers from importing TensorFlow/Keras (sentence-transformers
# only needs PyTorch).  This must be set *before* any sentence-transformers or
# transformers import happens anywhere in the process.
os.environ.setdefault("TRANSFORMERS_NO_TF", "1")
os.environ.setdefault("TRANSFORMERS_NO_FLAX", "1")
os.environ.setdefault("TF_USE_LEGACY_KERAS", "1")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")

from dotenv import load_dotenv

# Load variables from .env if present (local dev). On Streamlit Community Cloud
# the same variables are injected through the app's secrets manager.
load_dotenv()

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR: Path = Path(__file__).resolve().parent.parent
DATA_DIR: Path = BASE_DIR / "data"
FAQ_PDF_PATH: Path = DATA_DIR / "GigaCorp_Comprehensive_FAQ.pdf"

# ChromaDB persists embeddings here so they are only computed once.
CHROMA_DIR: Path = BASE_DIR / "chroma_db"
CHROMA_COLLECTION: str = "gigacorp_faq"

# ---------------------------------------------------------------------------
# Embeddings
# ---------------------------------------------------------------------------
EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"

# ---------------------------------------------------------------------------
# Text splitting
# ---------------------------------------------------------------------------
CHUNK_SIZE: int = 800
CHUNK_OVERLAP: int = 150

# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------
RETRIEVAL_K: int = 4  # number of chunks to fetch per query

# ---------------------------------------------------------------------------
# LLM providers
# ---------------------------------------------------------------------------
GROQ_API_KEY: str | None = os.getenv("GROQ_API_KEY")
GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

GOOGLE_API_KEY: str | None = os.getenv("GOOGLE_API_KEY")
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

# ---------------------------------------------------------------------------
# Conversation memory
# ---------------------------------------------------------------------------
MEMORY_K: int = 6  # number of past (human+ai) turns to keep in the buffer

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------
SYSTEM_PROMPT: str = (
    "You are GigaCorp's friendly customer-support assistant. "
    "Answer the user's question using ONLY the provided FAQ context. "
    "If the context does not contain the answer, say you don't have that "
    "information and suggest contacting human support. "
    "Always cite the source page number(s) for the facts you use."
)
