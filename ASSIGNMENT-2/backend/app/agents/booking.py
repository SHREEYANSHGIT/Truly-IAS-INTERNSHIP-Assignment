"""Booking Specialist node — powered by Google Gemini with Groq fallback.

Manages calendar tool execution, tracks slot details, prompts the user for
missing information, and negotiates alternative slots when a requested slot
is taken. Resolves relative dates ("tomorrow", "next Monday") to absolute
YYYY-MM-DD strings before executing any tools.

If Gemini is unavailable (quota exceeded, rate limit, network error), the
agent automatically falls back to Groq (llama-3.3-70b-versatile) so the
user experience is uninterrupted.
"""

from __future__ import annotations

import logging
import re
from datetime import date

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq

from ..config import get_settings
from ..state import BookingState
from ..tools.availability import check_availability
from ..tools.cancel import cancel_slot
from ..tools.list_bookings import list_bookings
from ..tools.notify import send_booking_notification
from ..tools.reschedule import reschedule_slot
from ..tools.reserve import reserve_slot
from ..utils import resolve_relative_date, validate_date, validate_time

logger = logging.getLogger(__name__)

BOOKING_SYSTEM_PROMPT = """You are the Booking Specialist for a scheduling assistant. You manage calendar bookings using six tools.

YOUR TOOLS:
1. check_availability(date) — Check which time slots are free on a given date (YYYY-MM-DD).
2. reserve_slot(date, time, email) — Reserve a specific slot. Requires date (YYYY-MM-DD), time (HH:MM 24h), and a valid email.
3. send_booking_notification(email, details, webhook_url) — Send a booking confirmation to the user's webhook.
4. list_bookings(email) — List all existing bookings for a given email address. Use this when the user asks to see their bookings.
5. cancel_slot(date, time, email) — Cancel (delete) an existing booking. Requires the date and time of the booking to cancel.
6. reschedule_slot(old_date, old_time, new_date, new_time, email) — Move an existing booking to a new date/time. The original booking is cancelled and the new slot is reserved atomically.

WORKFLOW RULES:
1. DATE NORMALIZATION: Before calling any tool, you MUST resolve relative dates to absolute YYYY-MM-DD. For example, if the user says "tomorrow", compute the actual date. If the user says "next Friday", compute the actual date. Always use absolute YYYY-MM-DD dates in tool calls.
2. MISSING INFORMATION: If the user has not provided a date or time, ask them for the missing information. Do NOT call tools until you have all required parameters.
3. CHECK FIRST: Always call check_availability before reserving. If the requested slot is taken, propose 2-3 alternative free slots from the availability results and ask the user to pick one.
4. NEGOTIATION: Never fail silently. If a slot is taken or a tool fails, negotiate alternatives with the user.
5. CONFIRMATION: After a successful reservation, call send_booking_notification with the booking details and the webhook_url (if provided). Then confirm the booking to the user.
6. LOGGED-IN USER: The user is authenticated. Their email is {user_email}. Use this email automatically for reserve_slot, list_bookings, cancel_slot, and reschedule_slot — do NOT ask the user for their email. If the email is "unknown", then ask for it.
7. LISTING BOOKINGS: When the user asks to see their bookings (e.g., "show me my bookings", "what are my appointments"), use the list_bookings tool with their email.
8. CANCELLING BOOKINGS: When the user asks to cancel or remove a booking, use list_bookings first to find the exact date/time, then call cancel_slot. Confirm the cancellation with the user.
9. RESCHEDULING BOOKINGS: When the user asks to reschedule or move a booking, use list_bookings first to find the exact old date/time, then call reschedule_slot with the old and new date/time. If the new slot is taken, propose alternatives from check_availability.

CURRENT DATE: {today}
LOGGED-IN USER EMAIL: {user_email}

Be concise, friendly, and helpful. When proposing alternatives, list them clearly."""


_TOOLS = [
    check_availability,
    reserve_slot,
    send_booking_notification,
    list_bookings,
    cancel_slot,
    reschedule_slot,
]


def _get_llm() -> ChatGoogleGenerativeAI:
    """Build the Gemini Chat model with tools bound."""
    settings = get_settings()
    llm = ChatGoogleGenerativeAI(
        google_api_key=settings.google_api_key,
        model="gemini-2.5-flash",
        temperature=0.3,
    )
    return llm.bind_tools(_TOOLS)


def _get_groq_llm() -> ChatGroq:
    """Build the Groq Chat model with tools bound (fallback)."""
    settings = get_settings()
    llm = ChatGroq(
        groq_api_key=settings.groq_api_key,
        model_name="llama-3.3-70b-versatile",
        temperature=0.3,
    )
    return llm.bind_tools(_TOOLS)


def _invoke_with_fallback(messages: list):
    """Invoke Gemini first; fall back to Groq on any error.

    Catches quota/rate-limit/network errors from Gemini and retries the
    same messages with Groq so the user experience is uninterrupted.
    """
    try:
        return _get_llm().invoke(messages)
    except Exception as exc:  # noqa: BLE001 — broad catch for fallback
        logger.warning("Gemini invoke failed (%s). Falling back to Groq.", exc)
        return _get_groq_llm().invoke(messages)


def _extract_relative_dates(text: str, today: date) -> str:
    """Pre-process the latest user message to resolve relative dates.

    Returns the text with relative date expressions replaced by absolute
    YYYY-MM-DD dates so the LLM sees concrete dates.
    """
    if not text:
        return text

    # Common relative date patterns to resolve
    patterns = [
        r"\btomorrow\b",
        r"\btoday\b",
        r"\byesterday\b",
        r"\bnext\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
        r"\bin\s+\d+\s+(day|week)s?\b",
    ]

    result = text
    for pattern in patterns:
        matches = re.finditer(pattern, result, re.IGNORECASE)
        # Process matches in reverse to preserve indices
        for match in reversed(list(matches)):
            matched_text = match.group(0)
            resolved = resolve_relative_date(matched_text, today)
            if resolved:
                result = result[: match.start()] + f"{matched_text} ({resolved})" + result[match.end():]

    return result


def booking_node(state: BookingState) -> dict:
    """Booking Specialist node.

    Invokes Gemini with tool-binding. If the model requests tool calls, they
    are executed inline (check_availability, reserve_slot, send_booking_notification).
    If the model produces a final text response, it is added as an AIMessage.
    """
    today = date.today()
    messages = list(state["messages"])
    webhook_url = state.get("webhook_url") or ""
    user_email = state.get("user_email") or ""

    # Pre-process the latest human message to resolve relative dates
    if messages and isinstance(messages[-1], HumanMessage):
        original = messages[-1].content
        resolved = _extract_relative_dates(original, today)
        if resolved != original:
            messages[-1] = HumanMessage(content=resolved)

    system_prompt = BOOKING_SYSTEM_PROMPT.format(
        today=today.isoformat(),
        user_email=user_email if user_email else "unknown",
    )
    # Build the full message list with the system prompt
    llm_messages = [SystemMessage(content=system_prompt)] + messages

    # Invoke the model (Gemini with Groq fallback)
    response = _invoke_with_fallback(llm_messages)

    # If the model made tool calls, execute them and re-invoke for a final answer
    if hasattr(response, "tool_calls") and response.tool_calls:
        return _handle_tool_calls(response, llm_messages, webhook_url, user_email, state)

    # No tool calls — return the text response
    content = response.content if isinstance(response.content, str) else str(response.content)
    return {
        "messages": [AIMessage(content=content, name="booking")],
        "current_agent": "booking",
    }


def _handle_tool_calls(
    response, llm_messages: list, webhook_url: str, user_email: str, state: BookingState
) -> dict:
    """Execute tool calls from the model and re-invoke for a final response.

    Loops up to 5 times to allow multi-step tool usage (check → reserve → notify,
    or list → cancel/reschedule). Auto-injects the authenticated user's email
    into reserve_slot, list_bookings, cancel_slot, and reschedule_slot calls so
    the user doesn't need to provide it each time.
    """
    tools_map = {
        "check_availability": check_availability,
        "reserve_slot": reserve_slot,
        "send_booking_notification": send_booking_notification,
        "list_bookings": list_bookings,
        "cancel_slot": cancel_slot,
        "reschedule_slot": reschedule_slot,
    }

    all_new_messages = [response]  # The AIMessage with tool_calls

    max_iterations = 5
    for _ in range(max_iterations):
        tool_messages = []
        for tool_call in response.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]

            # Inject webhook_url into send_booking_notification if missing or empty
            if tool_name == "send_booking_notification" and not tool_args.get("webhook_url"):
                tool_args["webhook_url"] = webhook_url

            # Auto-inject the authenticated user's email into reserve_slot
            if tool_name == "reserve_slot" and user_email:
                tool_args["email"] = user_email

            # Auto-inject the authenticated user's email into list_bookings
            if tool_name == "list_bookings" and user_email:
                tool_args["email"] = user_email

            # Auto-inject the authenticated user's email into cancel_slot
            if tool_name == "cancel_slot" and user_email:
                tool_args["email"] = user_email

            # Auto-inject the authenticated user's email into reschedule_slot
            if tool_name == "reschedule_slot" and user_email:
                tool_args["email"] = user_email

            logger.info("Executing tool: %s with args: %s", tool_name, tool_args)

            tool_fn = tools_map.get(tool_name)
            if tool_fn is None:
                tool_result = f"Error: unknown tool '{tool_name}'"
            else:
                tool_result = tool_fn.invoke(tool_args)

            tool_messages.append(
                ToolMessage(
                    content=str(tool_result),
                    tool_call_id=tool_call["id"],
                    name=tool_name,
                )
            )

        all_new_messages.extend(tool_messages)

        # Re-invoke the model with the tool results (Gemini with Groq fallback)
        updated_messages = llm_messages + all_new_messages
        response = _invoke_with_fallback(updated_messages)
        all_new_messages.append(response)

        # If no more tool calls, we have the final answer
        if not (hasattr(response, "tool_calls") and response.tool_calls):
            break

    # Extract the final text response
    content = response.content if isinstance(response.content, str) else str(response.content)

    # Update pending_booking if a reservation was successful
    pending_booking = state.get("pending_booking")
    for msg in all_new_messages:
        if isinstance(msg, ToolMessage) and msg.name == "reserve_slot":
            if "True" in msg.content and "success" in msg.content.lower():
                # Try to extract booking details from the tool result
                pending_booking = _extract_booking_from_result(msg.content)

    return {
        "messages": [AIMessage(content=content, name="booking")],
        "current_agent": "booking",
        "pending_booking": pending_booking,
    }


def _extract_booking_from_result(result_str: str) -> dict | None:
    """Attempt to extract booking details from a reserve_slot tool result."""
    # The tool result is a stringified dict; do a simple parse
    try:
        import ast

        result = ast.literal_eval(result_str)
        if isinstance(result, dict) and result.get("success") and result.get("booking"):
            return result["booking"]
    except (ValueError, SyntaxError):
        pass
    return None


def should_continue_booking(state: BookingState) -> str:
    """Conditional edge after the booking node.

    Since tool calls are handled inline within the booking node, we always
    route to "end" after the booking node produces a response. The
    conversation continues when the user sends the next message.
    """
    return "end"
