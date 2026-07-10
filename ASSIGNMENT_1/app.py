"""GigaCorp Customer Support Chatbot — Streamlit entry point.

Run locally with:
    streamlit run app.py
"""

from __future__ import annotations

import logging
import sys
import time

import streamlit as st

# Ensure the project root is importable when running `streamlit run app.py`.
sys.path.insert(0, ".")

from src import config  # noqa: E402
from src.llm import LLMUnavailableError, answer_query, get_llm  # noqa: E402
from src.memory import ConversationMemory, create_memory  # noqa: E402
from src.vectorstore import (  # noqa: E402
    build_vectorstore,
    format_context,
    get_sources,
    retrieve,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="GigaCorp Support Assistant",
    page_icon="🎧",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Custom CSS — modern, glassmorphic, animated UI
# ---------------------------------------------------------------------------
CUSTOM_CSS = """
<style>
/* ---------- Global ---------- */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}

.stApp {
    background: linear-gradient(135deg, #0F172A 0%, #1E1B4B 50%, #0F172A 100%);
    background-attachment: fixed;
}

/* Animated background orbs */
.stApp::before {
    content: '';
    position: fixed;
    top: -50%;
    left: -50%;
    width: 200%;
    height: 200%;
    background: radial-gradient(circle at 20% 80%, rgba(99, 102, 241, 0.08) 0%, transparent 50%),
                radial-gradient(circle at 80% 20%, rgba(168, 85, 247, 0.08) 0%, transparent 50%),
                radial-gradient(circle at 50% 50%, rgba(14, 165, 233, 0.05) 0%, transparent 50%);
    animation: floatOrbs 20s ease-in-out infinite;
    z-index: 0;
    pointer-events: none;
}

@keyframes floatOrbs {
    0%, 100% { transform: translate(0, 0) rotate(0deg); }
    33% { transform: translate(-2%, -2%) rotate(120deg); }
    66% { transform: translate(2%, 2%) rotate(240deg); }
}

/* ---------- Main content layering ---------- */
.main .block-container {
    position: relative;
    z-index: 1;
    padding-top: 0rem;
    max-width: 900px;
}

/* ---------- Hero header ---------- */
.hero-header {
    background: linear-gradient(135deg, rgba(99, 102, 241, 0.15) 0%, rgba(168, 85, 247, 0.15) 100%);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid rgba(99, 102, 241, 0.2);
    border-radius: 24px;
    padding: 2rem 2.5rem;
    margin-bottom: 1.5rem;
    text-align: center;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
    animation: fadeInDown 0.6s ease-out;
}

.hero-icon {
    font-size: 3rem;
    display: inline-block;
    animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
    0%, 100% { transform: scale(1); }
    50% { transform: scale(1.1); }
}

.hero-title {
    font-size: 2rem;
    font-weight: 800;
    background: linear-gradient(135deg, #818CF8 0%, #C084FC 50%, #38BDF8 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin: 0.5rem 0;
    letter-spacing: -0.02em;
}

.hero-subtitle {
    color: #94A3B8;
    font-size: 0.95rem;
    font-weight: 400;
    margin-top: 0.5rem;
}

.hero-badges {
    display: flex;
    justify-content: center;
    gap: 0.75rem;
    margin-top: 1rem;
    flex-wrap: wrap;
}

.hero-badge {
    background: rgba(99, 102, 241, 0.1);
    border: 1px solid rgba(99, 102, 241, 0.3);
    border-radius: 999px;
    padding: 0.3rem 0.9rem;
    font-size: 0.75rem;
    font-weight: 500;
    color: #A5B4FC;
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
}

/* ---------- Status pills ---------- */
.status-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.35rem 0.85rem;
    border-radius: 999px;
    font-size: 0.8rem;
    font-weight: 600;
    margin: 0.2rem 0;
}

.status-pill.online {
    background: rgba(34, 197, 94, 0.15);
    border: 1px solid rgba(34, 197, 94, 0.4);
    color: #4ADE80;
}

.status-pill.offline {
    background: rgba(239, 68, 68, 0.15);
    border: 1px solid rgba(239, 68, 68, 0.4);
    color: #F87171;
}

.status-pill.info {
    background: rgba(56, 189, 248, 0.15);
    border: 1px solid rgba(56, 189, 248, 0.4);
    color: #38BDF8;
}

.status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    display: inline-block;
}

.status-dot.online { background: #4ADE80; box-shadow: 0 0 8px #4ADE80; animation: blink 1.5s infinite; }
.status-dot.offline { background: #F87171; }
.status-dot.info { background: #38BDF8; }

@keyframes blink {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
}

/* ---------- Sidebar ---------- */
section[data-testid="stSidebar"] {
    background: rgba(15, 23, 42, 0.7);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border-right: 1px solid rgba(99, 102, 241, 0.15);
}

section[data-testid="stSidebar"] .stMarkdown h1,
section[data-testid="stSidebar"] .stMarkdown h2,
section[data-testid="stSidebar"] .stMarkdown h3 {
    color: #818CF8;
}

.sidebar-card {
    background: rgba(30, 41, 59, 0.6);
    border: 1px solid rgba(99, 102, 241, 0.15);
    border-radius: 16px;
    padding: 1rem;
    margin: 0.5rem 0;
    backdrop-filter: blur(10px);
}

.config-item {
    display: flex;
    justify-content: space-between;
    padding: 0.4rem 0;
    border-bottom: 1px solid rgba(99, 102, 241, 0.08);
    font-size: 0.82rem;
}

.config-item:last-child { border-bottom: none; }
.config-item .label { color: #94A3B8; }
.config-item .value { color: #A5B4FC; font-weight: 600; font-family: 'JetBrains Mono', monospace; }

/* ---------- Chat messages ---------- */
.stChatMessage {
    animation: fadeInUp 0.4s ease-out;
}

[data-testid="stChatMessageContent"] {
    background: rgba(30, 41, 59, 0.6);
    border: 1px solid rgba(99, 102, 241, 0.12);
    border-radius: 16px;
    padding: 1rem 1.25rem;
    backdrop-filter: blur(10px);
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
}

[data-testid="stChatMessageContent"]:hover {
    border-color: rgba(99, 102, 241, 0.3);
    transition: border-color 0.3s ease;
}

/* ---------- Source cards ---------- */
.source-card {
    background: linear-gradient(135deg, rgba(99, 102, 241, 0.08) 0%, rgba(168, 85, 247, 0.08) 100%);
    border: 1px solid rgba(99, 102, 241, 0.2);
    border-radius: 12px;
    padding: 0.75rem 1rem;
    margin: 0.5rem 0;
    transition: all 0.3s ease;
}

.source-card:hover {
    border-color: rgba(99, 102, 241, 0.5);
    transform: translateY(-2px);
    box-shadow: 0 4px 20px rgba(99, 102, 241, 0.15);
}

.source-label {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    background: rgba(99, 102, 241, 0.2);
    color: #A5B4FC;
    padding: 0.2rem 0.6rem;
    border-radius: 6px;
    font-size: 0.75rem;
    font-weight: 700;
    margin-bottom: 0.4rem;
}

.source-preview {
    color: #94A3B8;
    font-size: 0.82rem;
    line-height: 1.5;
    margin-top: 0.3rem;
}

/* ---------- Suggested questions ---------- */
.suggestion-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.75rem;
    margin: 1rem 0;
}

.suggestion-card {
    background: rgba(30, 41, 59, 0.5);
    border: 1px solid rgba(99, 102, 241, 0.2);
    border-radius: 14px;
    padding: 1rem;
    cursor: pointer;
    transition: all 0.3s ease;
    text-align: left;
    width: 100%;
    color: #CBD5E1;
    font-size: 0.85rem;
    font-weight: 500;
}

.suggestion-card:hover {
    background: rgba(99, 102, 241, 0.15);
    border-color: rgba(99, 102, 241, 0.5);
    transform: translateY(-3px);
    box-shadow: 0 6px 24px rgba(99, 102, 241, 0.2);
    color: #E0E7FF;
}

.suggestion-icon {
    font-size: 1.2rem;
    margin-bottom: 0.4rem;
    display: block;
}

/* ---------- Empty state ---------- */
.empty-state {
    text-align: center;
    padding: 3rem 1rem;
    animation: fadeInUp 0.6s ease-out;
}

.empty-state-icon {
    font-size: 4rem;
    opacity: 0.5;
    animation: float 3s ease-in-out infinite;
}

@keyframes float {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(-10px); }
}

.empty-state-text {
    color: #64748B;
    font-size: 1rem;
    margin-top: 1rem;
}

/* ---------- Chat input ---------- */
[data-testid="stChatInput"] {
    position: relative;
    z-index: 1;
}

[data-testid="stChatInputTextArea"] {
    background: rgba(30, 41, 59, 0.8) !important;
    border: 1px solid rgba(99, 102, 241, 0.3) !important;
    border-radius: 16px !important;
    color: #F1F5F9 !important;
    backdrop-filter: blur(10px);
    transition: all 0.3s ease;
}

[data-testid="stChatInputTextArea"]:focus {
    border-color: #6366F1 !important;
    box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.2) !important;
}

/* ---------- Buttons ---------- */
.stButton > button {
    border-radius: 12px;
    font-weight: 600;
    transition: all 0.3s ease;
    border: 1px solid rgba(99, 102, 241, 0.3);
}

.stButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(99, 102, 241, 0.3);
}

.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #6366F1 0%, #8B5CF6 100%);
    border: none;
}

/* ---------- Expanders ---------- */
.streamlit-expander {
    background: rgba(30, 41, 59, 0.4);
    border: 1px solid rgba(99, 102, 241, 0.15);
    border-radius: 12px;
    margin-top: 0.5rem;
}

.streamlit-expander header {
    font-weight: 600;
    color: #A5B4FC;
}

/* ---------- Animations ---------- */
@keyframes fadeInDown {
    from { opacity: 0; transform: translateY(-20px); }
    to { opacity: 1; transform: translateY(0); }
}

@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(20px); }
    to { opacity: 1; transform: translateY(0); }
}

/* ---------- Scrollbar ---------- */
::-webkit-scrollbar { width: 8px; }
::-webkit-scrollbar-track { background: rgba(15, 23, 42, 0.5); }
::-webkit-scrollbar-thumb {
    background: rgba(99, 102, 241, 0.3);
    border-radius: 4px;
}
::-webkit-scrollbar-thumb:hover { background: rgba(99, 102, 241, 0.5); }

/* ---------- Typing indicator ---------- */
.typing-indicator {
    display: flex;
    gap: 4px;
    padding: 0.5rem 0;
}

.typing-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #6366F1;
    animation: typingBounce 1.4s infinite ease-in-out;
}

.typing-dot:nth-child(2) { animation-delay: 0.2s; }
.typing-dot:nth-child(3) { animation-delay: 0.4s; }

@keyframes typingBounce {
    0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
    40% { transform: scale(1); opacity: 1; }
}

/* ---------- Divider ---------- */
hr {
    border-color: rgba(99, 102, 241, 0.15) !important;
    margin: 1rem 0;
}

/* ---------- Footer ---------- */
.app-footer {
    text-align: center;
    color: #475569;
    font-size: 0.75rem;
    padding: 1.5rem 0 0.5rem 0;
    border-top: 1px solid rgba(99, 102, 241, 0.1);
    margin-top: 2rem;
}
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Session-state initialisation
# ---------------------------------------------------------------------------
def init_state() -> None:
    """Initialise Streamlit session state on first load."""
    if "messages" not in st.session_state:
        st.session_state.messages = []  # list of {"role","content","sources"}
    if "memory" not in st.session_state:
        st.session_state.memory = create_memory()
    if "llm" not in st.session_state:
        try:
            st.session_state.llm, st.session_state.provider = get_llm()
        except LLMUnavailableError as exc:
            st.session_state.llm = None
            st.session_state.provider = None
            st.session_state.llm_error = str(exc)
    if "vectorstore_ready" not in st.session_state:
        st.session_state.vectorstore_ready = False


init_state()


# ---------------------------------------------------------------------------
# Hero header
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div class="hero-header">
        <div class="hero-icon">🎧</div>
        <div class="hero-title">GigaCorp Support Assistant</div>
        <div class="hero-subtitle">AI-powered answers sourced directly from the official GigaCorp FAQ</div>
        <div class="hero-badges">
            <span class="hero-badge">⚡ Instant Answers</span>
            <span class="hero-badge">📚 Source Cited</span>
            <span class="hero-badge">🧠 Context Aware</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Sidebar — status & controls
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## 🎛️ Control Panel")

    # Provider status card
    st.markdown('<div class="sidebar-card">', unsafe_allow_html=True)
    st.markdown("#### 🤖 LLM Provider")
    provider = st.session_state.get("provider")
    if provider:
        st.markdown(
            f'<div class="status-pill online"><span class="status-dot online"></span>{provider} — Active</div>',
            unsafe_allow_html=True,
        )
    elif st.session_state.get("llm_error"):
        st.markdown(
            '<div class="status-pill offline"><span class="status-dot offline"></span>No provider</div>',
            unsafe_allow_html=True,
        )
        st.error(st.session_state["llm_error"])
    else:
        st.markdown(
            '<div class="status-pill offline"><span class="status-dot offline"></span>Not configured</div>',
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)

    # Vector store status card
    st.markdown('<div class="sidebar-card">', unsafe_allow_html=True)
    st.markdown("#### 📚 Knowledge Base")
    if st.session_state.vectorstore_ready:
        st.markdown(
            f'<div class="status-pill info"><span class="status-dot info"></span>{config.CHROMA_COLLECTION} ready</div>',
            unsafe_allow_html=True,
        )
    else:
        if st.button("🔨 Build FAQ Index", type="primary", use_container_width=True):
            with st.spinner("Loading PDF, chunking and generating embeddings…"):
                try:
                    build_vectorstore()
                    st.session_state.vectorstore_ready = True
                    st.success("FAQ index built successfully!")
                    st.rerun()
                except Exception as exc:  # noqa: BLE001
                    st.error(f"Failed to build index: {exc}")
                    logger.exception("Vector store build failed")
    st.markdown("</div>", unsafe_allow_html=True)

    # Conversation controls
    st.markdown('<div class="sidebar-card">', unsafe_allow_html=True)
    st.markdown("#### 💬 Conversation")
    msg_count = len(st.session_state.messages)
    st.markdown(
        f'<div class="status-pill info"><span class="status-dot info"></span>{msg_count} messages</div>',
        unsafe_allow_html=True,
    )
    if st.button("🗑️ Clear Conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.memory = create_memory()
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    st.divider()

    # Configuration details
    st.markdown("#### ⚙️ Configuration")
    st.markdown(
        """
        <div class="sidebar-card">
            <div class="config-item"><span class="label">Embedding</span><span class="value">all-MiniLM-L6-v2</span></div>
            <div class="config-item"><span class="label">Chunk size</span><span class="value">800 / 150</span></div>
            <div class="config-item"><span class="label">Top-K</span><span class="value">4</span></div>
            <div class="config-item"><span class="label">Memory</span><span class="value">6 turns</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()
    st.markdown(
        """
        <div style="text-align:center; color:#475569; font-size:0.75rem; padding-top:1rem;">
            Built with ❤️ using LangChain + RAG<br/>
            Groq · Gemini · ChromaDB
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Auto-build the vector store on first load (non-blocking)
# ---------------------------------------------------------------------------
if not st.session_state.vectorstore_ready and st.session_state.llm is not None:
    try:
        with st.spinner("Initialising FAQ knowledge base…"):
            build_vectorstore()
            st.session_state.vectorstore_ready = True
    except Exception as exc:  # noqa: BLE001
        st.error(f"Could not load the FAQ knowledge base: {exc}")
        logger.exception("Auto vector store build failed")


# ---------------------------------------------------------------------------
# Suggested questions (shown when no messages yet)
# ---------------------------------------------------------------------------
SUGGESTED_QUESTIONS = [
    ("🚚", "Do you ship internationally?"),
    ("↩️", "What is your return policy?"),
    ("🕐", "What are your business hours?"),
    ("💎", "What service tiers do you offer?"),
]


def render_suggestions() -> None:
    """Render clickable suggestion cards."""
    st.markdown(
        '<div class="empty-state"><div class="empty-state-icon">💬</div>'
        '<div class="empty-state-text">Ask me anything about GigaCorp!</div></div>',
        unsafe_allow_html=True,
    )
    st.markdown("#### ✨ Try these questions:")
    cols = st.columns(2)
    for idx, (icon, question) in enumerate(SUGGESTED_QUESTIONS):
        with cols[idx % 2]:
            if st.button(
                f"{icon}  {question}",
                key=f"sugg_{idx}",
                use_container_width=True,
                help="Click to ask this question",
            ):
                st.session_state.pending_prompt = question
                st.rerun()


# ---------------------------------------------------------------------------
# Handle pending prompt from suggestions
# ---------------------------------------------------------------------------
pending = st.session_state.pop("pending_prompt", None)


# ---------------------------------------------------------------------------
# Display chat history
# ---------------------------------------------------------------------------
def render_sources(sources: list[dict]) -> None:
    """Render source citations as styled cards inside an expander."""
    if not sources:
        return
    with st.expander("📚 Sources & Citations", expanded=False):
        for src in sources:
            st.markdown(
                f"""
                <div class="source-card">
                    <span class="source-label">📄 Source {src['index']} · Page {src['page']}</span>
                    <div class="source-preview">{src['preview']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar="🧑‍💼" if msg["role"] == "user" else "🤖"):
        st.markdown(msg["content"])
        if msg.get("sources"):
            render_sources(msg["sources"])


# ---------------------------------------------------------------------------
# Empty state with suggestions
# ---------------------------------------------------------------------------
if not st.session_state.messages:
    render_suggestions()


# ---------------------------------------------------------------------------
# Chat input
# ---------------------------------------------------------------------------
prompt = st.chat_input("Ask a support question…") or pending

if prompt:
    if st.session_state.llm is None:
        st.error("⚠️ Please configure an LLM API key before asking questions.")
    elif not st.session_state.vectorstore_ready:
        st.warning("⏳ The FAQ index is still loading. Please wait a moment…")
    else:
        # Show the user's message immediately
        with st.chat_message("user", avatar="🧑‍💼"):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Typing indicator
        with st.chat_message("assistant", avatar="🤖"):
            st.markdown(
                '<div class="typing-indicator">'
                '<span class="typing-dot"></span>'
                '<span class="typing-dot"></span>'
                '<span class="typing-dot"></span>'
                '</div>',
                unsafe_allow_html=True,
            )

        # Retrieve relevant chunks
        with st.spinner("🔍 Searching the FAQ…"):
            docs = retrieve(prompt)
            context = format_context(docs)
            sources = get_sources(docs)

        # Generate answer with conversation memory
        with st.spinner("✨ Generating answer…"):
            history = st.session_state.memory.to_history()
            try:
                answer = answer_query(
                    st.session_state.llm, context, prompt, history
                )
            except Exception as exc:  # noqa: BLE001
                logger.exception("LLM call failed")
                answer = (
                    "I'm sorry, I couldn't generate an answer right now. "
                    f"Error: {exc}"
                )

        # Update memory
        st.session_state.memory.add("human", prompt)
        st.session_state.memory.add("ai", answer)

        # Store assistant reply so it renders on rerun
        st.session_state.messages.append(
            {"role": "assistant", "content": answer, "sources": sources}
        )

        # Rerun to render the full conversation cleanly
        st.rerun()

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.markdown(
    '<div class="app-footer">'
    "GigaCorp Support Assistant · Powered by RAG · "
    "Answers are generated from the official FAQ and may contain citations."
    "</div>",
    unsafe_allow_html=True,
)
