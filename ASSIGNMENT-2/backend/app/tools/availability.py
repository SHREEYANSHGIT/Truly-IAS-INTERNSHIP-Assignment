"""check_availability tool — queries the SQLite slots table for a given date."""

from __future__ import annotations

from langchain_core.tools import tool

from ..db import get_free_slots, get_taken_slots
from ..utils import generate_time_slots, validate_date


@tool
def check_availability(date: str) -> dict:
    """Check availability for a given date.

    Args:
        date: The date to check in YYYY-MM-DD format.

    Returns:
        A dict with ``available`` (bool), ``taken_slots`` (list), and
        ``free_slots`` (list of HH:MM strings).
    """
    if not validate_date(date):
        return {
            "available": False,
            "error": f"Invalid date format: '{date}'. Expected YYYY-MM-DD.",
            "taken_slots": [],
            "free_slots": [],
        }

    taken = get_taken_slots(date)
    free = get_free_slots(date)

    return {
        "available": len(free) > 0,
        "date": date,
        "taken_slots": taken,
        "free_slots": free,
        "all_slots": generate_time_slots(),
    }
