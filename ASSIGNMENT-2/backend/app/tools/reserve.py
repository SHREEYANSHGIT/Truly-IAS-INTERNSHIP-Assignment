"""reserve_slot tool — saves an appointment slot in the SQLite database."""

from __future__ import annotations

from langchain_core.tools import tool

from ..db import insert_slot, is_slot_available
from ..utils import validate_date, validate_time


@tool
def reserve_slot(date: str, time: str, email: str) -> dict:
    """Reserve an appointment slot.

    Args:
        date: The appointment date in YYYY-MM-DD format.
        time: The appointment time in HH:MM (24h) format.
        email: The user's email address for the booking.

    Returns:
        A dict with ``success`` (bool) and ``message`` (str).
    """
    if not validate_date(date):
        return {"success": False, "message": f"Invalid date format: '{date}'. Expected YYYY-MM-DD."}

    if not validate_time(time):
        return {"success": False, "message": f"Invalid time format: '{time}'. Expected HH:MM (24h)."}

    if not email or "@" not in email:
        return {"success": False, "message": "A valid email address is required."}

    # Double-check availability before inserting
    if not is_slot_available(date, time):
        return {
            "success": False,
            "message": f"Sorry, the slot on {date} at {time} is already taken. Please choose another time.",
        }

    success = insert_slot(date, time, email)
    if success:
        return {
            "success": True,
            "message": f"Successfully reserved {date} at {time} for {email}.",
            "booking": {"date": date, "time": time, "email": email},
        }
    return {
        "success": False,
        "message": f"Could not reserve {date} at {time} — the slot was just taken. Please try another time.",
    }
