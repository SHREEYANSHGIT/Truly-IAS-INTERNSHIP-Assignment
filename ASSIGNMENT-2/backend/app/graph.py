"""LangGraph state machine definition.

Wires the Triage Agent and Booking Specialist into a StateGraph with
conditional routing. The graph is compiled with a SqliteSaver checkpointer
for conversation persistence.
"""

from __future__ import annotations

import logging
import os
import sqlite3

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

from .agents.booking import booking_node, should_continue_booking
from .agents.triage import should_route_after_triage, triage_node
from .db import get_db_path, init_db
from .state import BookingState

logger = logging.getLogger(__name__)

# Module-level compiled graph and checkpointer
_compiled_graph = None
_checkpointer = None
_checkpoint_conn = None


def _build_graph():
    """Build and compile the LangGraph state machine."""
    global _compiled_graph, _checkpointer, _checkpoint_conn

    if _compiled_graph is not None:
        return _compiled_graph, _checkpointer

    # Initialize the database (slots table + seed data)
    init_db()

    # Set up the SQLite checkpointer for conversation persistence.
    # We create a persistent connection (not a context-managed one) so it
    # stays open for the lifetime of the application.
    db_path = get_db_path()
    _checkpoint_conn = sqlite3.connect(db_path, check_same_thread=False)
    _checkpointer = SqliteSaver(_checkpoint_conn)
    _checkpointer.setup()

    # Build the state graph
    workflow = StateGraph(BookingState)

    # Add nodes
    workflow.add_node("triage", triage_node)
    workflow.add_node("booking", booking_node)

    # Set entry point
    workflow.add_edge(START, "triage")

    # Conditional edge from triage: route to booking or end
    workflow.add_conditional_edges(
        "triage",
        should_route_after_triage,
        {
            "booking": "booking",
            "end": END,
        },
    )

    # Conditional edge from booking: always end (conversation continues on
    # next user message, state is persisted by the checkpointer)
    workflow.add_conditional_edges(
        "booking",
        should_continue_booking,
        {
            "end": END,
        },
    )

    # Compile with the checkpointer
    _compiled_graph = workflow.compile(checkpointer=_checkpointer)

    logger.info("LangGraph compiled with SqliteSaver checkpointer at %s", db_path)
    return _compiled_graph, _checkpointer


def get_graph():
    """Return the compiled graph, building it if necessary."""
    graph, _ = _build_graph()
    return graph


def get_checkpointer():
    """Return the SqliteSaver checkpointer."""
    _, checkpointer = _build_graph()
    return checkpointer


def invoke_graph(
    thread_id: str,
    message: str,
    webhook_url: str | None = None,
    user_email: str | None = None,
) -> dict:
    """Invoke the graph with a user message and return the final state.

    Args:
        thread_id: Unique conversation identifier (used for checkpointing).
        message: The user's message text.
        webhook_url: Optional webhook URL for notifications.
        user_email: The authenticated user's email for per-user data isolation.

    Returns:
        The final graph state dict containing ``messages``, ``pending_booking``,
        and ``current_agent``.
    """
    graph = get_graph()

    config = {"configurable": {"thread_id": thread_id}}

    # Build the input state
    input_state = {
        "messages": [HumanMessage(content=message)],
        "thread_id": thread_id,
        "user_email": user_email,
        "webhook_url": webhook_url,
        "current_agent": "triage",
    }

    # Invoke the graph
    result = graph.invoke(input_state, config=config)

    return result


def get_history(thread_id: str) -> list[dict]:
    """Retrieve the conversation history for a given thread.

    Returns a list of message dicts with ``role``, ``content``, and ``name``.
    """
    graph = get_graph()
    config = {"configurable": {"thread_id": thread_id}}

    try:
        state = graph.get_state(config)
        if state is None or state.values is None:
            return []

        messages = state.values.get("messages", [])
        history = []
        for msg in messages:
            role = "user"
            if msg.type == "ai":
                role = "assistant"
            elif msg.type == "system":
                continue
            elif msg.type == "tool":
                continue

            history.append({
                "role": role,
                "content": msg.content if isinstance(msg.content, str) else str(msg.content),
                "name": getattr(msg, "name", None),
            })
        return history
    except Exception as exc:
        logger.error("Failed to get history for thread %s: %s", thread_id, exc)
        return []
