"""TypedDict state schema for the LangGraph state machine."""

from __future__ import annotations

from typing import Annotated, Optional, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class BookingState(TypedDict):
    """State shared across all nodes in the scheduling graph.

    Attributes:
        messages: Conversation history (LangChain BaseMessage list). The
            ``add_messages`` reducer appends new messages instead of replacing.
        thread_id: Unique conversation/session identifier used by the
            SqliteSaver checkpointer.
        user_email: The authenticated user's email. Used to auto-fill the
            email in booking tools and to isolate data per user.
        pending_booking: Tracks an in-progress booking with date, time, and
            email. ``None`` when no booking is in flight.
        webhook_url: User-provided webhook endpoint for sending booking
            notifications. ``None`` when the user has not configured one.
        current_agent: Which agent is currently active ("triage" or "booking").
    """

    messages: Annotated[list[BaseMessage], add_messages]
    thread_id: str
    user_email: Optional[str]
    pending_booking: Optional[dict]
    webhook_url: Optional[str]
    current_agent: str
