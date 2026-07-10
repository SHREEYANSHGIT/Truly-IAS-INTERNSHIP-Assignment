"""LLM wrapper with Groq as the primary provider and Gemini as fallback.

The :func:`get_llm` helper tries to instantiate a Groq-backed model first.  If
the Groq API key is missing or the call fails at runtime, it transparently
falls back to Google Gemini.  The active provider name is exposed so the UI can
show which model answered.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from src import config

logger = logging.getLogger(__name__)


class LLMUnavailableError(RuntimeError):
    """Raised when no LLM provider can be initialised."""


def _build_groq() -> BaseChatModel | None:
    """Return a Groq chat model, or ``None`` if it cannot be configured."""
    if not config.GROQ_API_KEY:
        logger.warning("GROQ_API_KEY not set – skipping Groq provider")
        return None
    try:
        from langchain_groq import ChatGroq

        logger.info("Initialising Groq LLM (%s)", config.GROQ_MODEL)
        return ChatGroq(
            model=config.GROQ_MODEL,
            temperature=0.3,
            api_key=config.GROQ_API_KEY,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to initialise Groq: %s", exc)
        return None


def _build_gemini() -> BaseChatModel | None:
    """Return a Gemini chat model, or ``None`` if it cannot be configured."""
    if not config.GOOGLE_API_KEY:
        logger.warning("GOOGLE_API_KEY not set – skipping Gemini provider")
        return None
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI

        logger.info("Initialising Gemini LLM (%s)", config.GEMINI_MODEL)
        return ChatGoogleGenerativeAI(
            model=config.GEMINI_MODEL,
            temperature=0.3,
            google_api_key=config.GOOGLE_API_KEY,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to initialise Gemini: %s", exc)
        return None


def get_llm() -> tuple[BaseChatModel, str]:
    """Return ``(llm, provider_name)`` using Groq first, Gemini as fallback.

    Raises :class:`LLMUnavailableError` when neither provider is available.
    """
    groq = _build_groq()
    if groq is not None:
        return groq, "Groq"

    gemini = _build_gemini()
    if gemini is not None:
        return gemini, "Gemini"

    raise LLMUnavailableError(
        "No LLM provider available. Set GROQ_API_KEY and/or GOOGLE_API_KEY."
    )


def answer_query(
    llm: BaseChatModel,
    context: str,
    question: str,
    history: list[dict[str, str]] | None = None,
) -> str:
    """Generate an answer using the retrieved context and conversation history.

    Parameters
    ----------
    llm
        The chat model returned by :func:`get_llm`.
    context
        Formatted FAQ chunks (see :func:`vectorstore.format_context`).
    question
        The latest user question.
    history
        Optional list of ``{"role": "human"|"ai", "content": "..."}`` dicts
        representing the short-term conversation memory.
    """
    messages: list[Any] = [SystemMessage(content=config.SYSTEM_PROMPT)]

    # Inject the retrieved context as a system-level instruction.
    messages.append(
        SystemMessage(
            content=(
                "Use the following FAQ excerpts to answer the user's question. "
                "Cite the source page numbers when you use information from them.\n\n"
                f"{context}"
            )
        )
    )

    # Replay conversation history for follow-up continuity.
    if history:
        for turn in history:
            role = turn.get("role", "human")
            content = turn.get("content", "")
            if role == "ai":
                messages.append(AIMessage(content=content))
            else:
                messages.append(HumanMessage(content=content))

    messages.append(HumanMessage(content=question))
    response = llm.invoke(messages)
    return response.content
