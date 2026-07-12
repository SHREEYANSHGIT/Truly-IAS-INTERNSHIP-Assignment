"""Triage Agent node — powered by Groq.

Analyzes incoming user messages and decides routing:
- General queries → respond directly and end the turn.
- Booking/scheduling intent → route control to the Booking Specialist.
"""

from __future__ import annotations

import logging

from langchain_core.messages import AIMessage, SystemMessage
from langchain_groq import ChatGroq

from ..config import get_settings
from ..state import BookingState

logger = logging.getLogger(__name__)

TRIAGE_SYSTEM_PROMPT = """You are the Triage Agent for a scheduling assistant. Your job is to analyze the user's message and decide how to handle it.

RULES:
1. If the user's message is a general query (greeting, small talk, FAQ, questions about how things work, etc.), respond helpfully and conversationally. End your response naturally.
2. If the user expresses ANY intent to schedule, book, check, reserve, or manage an appointment/meeting/slot, you MUST respond with EXACTLY this token on the first line:
   ROUTE_TO_BOOKING
   Do not add any other text before or after this token. The Booking Specialist will take over.
3. Examples of booking intent: "Book tomorrow at 3pm", "I want to schedule a meeting", "Check availability for Friday", "Can I reserve a slot?", "I need an appointment next week".
4. Examples of general queries: "Hello", "What can you do?", "How does this work?", "Thanks!", "Tell me a joke".

Remember: when in doubt about whether something is a booking intent, route to the Booking Specialist by responding with ROUTE_TO_BOOKING."""


def _get_llm() -> ChatGroq:
    """Build the Groq Chat model for the Triage Agent."""
    settings = get_settings()
    return ChatGroq(
        groq_api_key=settings.groq_api_key,
        model_name="llama-3.3-70b-versatile",
        temperature=0.2,
    )


def triage_node(state: BookingState) -> dict:
    """Triage agent node: classify intent and either respond or route.

    Returns a state update dict. If routing to booking, sets
    ``current_agent`` to "booking" and does not add a message (the booking
    agent will handle it). If responding directly, adds an AIMessage and
    keeps ``current_agent`` as "triage".
    """
    messages = state["messages"]
    llm = _get_llm()

    # Build the message list with the system prompt
    llm_messages = [SystemMessage(content=TRIAGE_SYSTEM_PROMPT)] + list(messages)

    response = llm.invoke(llm_messages)
    content = response.content.strip() if isinstance(response.content, str) else str(response.content).strip()

    # Check for routing signal
    if content.upper().startswith("ROUTE_TO_BOOKING"):
        logger.info("Triage: routing to Booking Specialist")
        return {"current_agent": "booking"}

    # General query — respond directly
    logger.info("Triage: responding directly")
    return {
        "messages": [AIMessage(content=content, name="triage")],
        "current_agent": "triage",
    }


def should_route_after_triage(state: BookingState) -> str:
    """Conditional edge: decide where to go after the triage node."""
    if state.get("current_agent") == "booking":
        return "booking"
    return "end"
