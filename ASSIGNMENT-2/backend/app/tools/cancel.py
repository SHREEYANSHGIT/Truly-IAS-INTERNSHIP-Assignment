"""cancel_slot tool — cancels (deletes) an existing appointment from the SQLite database."""

from __future__ import annotations

from langchain_core.tools import tool

from ..db import cancel_slot as _cancel_slot
from ..utils import validate_date, validate_time


@tool
def cancel_slot(date: str, time: str, email: str) -> dict:
    """Cancel an existing appointment.

    Args:
        date: The appointment date in YYYY-MM-DD format.
        time: The appointment time in HH:MM (24h) format.
        email: The user's email address associated with the booking.

    Returns:
        A dict with ``success`` (bool) and ``message`` (str).
    """
    if not validate_date(date):
        return {"success": False, "message": f"Invalid date format: '{date}'. Expected YYYY-MM-DD."}

    if not validate_time(time):
        return {"success": False, "message": f"Invalid time format: '{time}'. Expected HH:MM (24h)."}

    if not email or "@" not in email:
        return {"success": False, "message": "A valid email address is required."}

    return _cancel_slot(date, time, email)
