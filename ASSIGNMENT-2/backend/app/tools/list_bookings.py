"""Tool to list existing bookings for a given email address."""

from __future__ import annotations

from langchain_core.tools import tool

from ..db import get_all_slots


@tool
def list_bookings(email: str) -> dict:
    """List all existing bookings for a given email address.

    Args:
        email: The email address to look up bookings for.

    Returns:
        A dict with the count of bookings and the list of bookings
        (date, time, email, created_at) sorted by date then time.
    """
    all_slots = get_all_slots()
    user_bookings = [s for s in all_slots if s["email"].lower() == email.lower()]

    if not user_bookings:
        return {
            "count": 0,
            "bookings": [],
            "message": f"No bookings found for {email}.",
        }

    # Sort by date then time
    user_bookings.sort(key=lambda b: (b["date"], b["time"]))

    return {
        "count": len(user_bookings),
        "bookings": user_bookings,
        "message": f"Found {len(user_bookings)} booking(s) for {email}.",
    }
