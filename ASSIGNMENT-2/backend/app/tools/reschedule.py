"""reschedule_slot tool — moves an existing booking to a new date/time atomically."""

from __future__ import annotations

from langchain_core.tools import tool

from ..db import reschedule_slot as _reschedule_slot
from ..utils import validate_date, validate_time


@tool
def reschedule_slot(
    old_date: str,
    old_time: str,
    new_date: str,
    new_time: str,
    email: str,
) -> dict:
    """Reschedule an existing appointment to a new date and time.

    The original booking is cancelled and the new slot is reserved in a single
    atomic transaction. If the new slot is already taken, the original booking
    is preserved unchanged.

    Args:
        old_date: The current appointment date in YYYY-MM-DD format.
        old_time: The current appointment time in HH:MM (24h) format.
        new_date: The new appointment date in YYYY-MM-DD format.
        new_time: The new appointment time in HH:MM (24h) format.
        email: The user's email address associated with the booking.

    Returns:
        A dict with ``success`` (bool) and ``message`` (str).
    """
    for label, value in [("old_date", old_date), ("new_date", new_date)]:
        if not validate_date(value):
            return {"success": False, "message": f"Invalid {label} format: '{value}'. Expected YYYY-MM-DD."}

    for label, value in [("old_time", old_time), ("new_time", new_time)]:
        if not validate_time(value):
            return {"success": False, "message": f"Invalid {label} format: '{value}'. Expected HH:MM (24h)."}

    if not email or "@" not in email:
        return {"success": False, "message": "A valid email address is required."}

    return _reschedule_slot(old_date, old_time, new_date, new_time, email)
