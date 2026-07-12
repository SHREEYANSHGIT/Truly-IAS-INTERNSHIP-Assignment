"""Date and time normalization utilities for the Booking Specialist.

Resolves relative dates like "tomorrow", "next Monday", "in 3 days" to
absolute YYYY-MM-DD strings based on the current date, and validates time
formats (HH:MM).
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta

from dateutil.relativedelta import relativedelta

# Standard business-hour slots (24h format) used for availability checks.
BUSINESS_HOURS = list(range(9, 18))  # 09:00 through 17:00

WEEKDAY_NAMES = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


def resolve_relative_date(text: str, today: date | None = None) -> str | None:
    """Resolve a natural-language date expression to YYYY-MM-DD.

    Supports:
      - "today"
      - "tomorrow"
      - "yesterday"
      - "next monday" / "next friday" etc.
      - "in N days" / "in N weeks"
      - Already-absolute dates "YYYY-MM-DD"

    Returns the YYYY-MM-DD string, or ``None`` if the expression cannot be
    parsed.
    """
    if today is None:
        today = date.today()

    text = text.strip().lower()

    # Already an absolute date
    if re.match(r"^\d{4}-\d{2}-\d{2}$", text):
        try:
            datetime.strptime(text, "%Y-%m-%d")
            return text
        except ValueError:
            return None

    if text == "today":
        return today.isoformat()

    if text == "tomorrow":
        return (today + timedelta(days=1)).isoformat()

    if text == "yesterday":
        return (today - timedelta(days=1)).isoformat()

    # "in N days" / "in N weeks"
    m = re.match(r"^in\s+(\d+)\s+(day|week)s?$", text)
    if m:
        n = int(m.group(1))
        unit = m.group(2)
        delta = timedelta(days=n) if unit == "day" else timedelta(weeks=n)
        return (today + delta).isoformat()

    # "next monday", "next friday", etc.
    m = re.match(r"^next\s+(\w+)$", text)
    if m and m.group(1) in WEEKDAY_NAMES:
        target_weekday = WEEKDAY_NAMES[m.group(1)]
        days_ahead = (target_weekday - today.weekday()) % 7
        if days_ahead == 0:
            days_ahead = 7  # "next" implies a future occurrence
        return (today + timedelta(days=days_ahead)).isoformat()

    # Bare weekday name -> next occurrence
    if text in WEEKDAY_NAMES:
        target_weekday = WEEKDAY_NAMES[text]
        days_ahead = (target_weekday - today.weekday()) % 7
        if days_ahead == 0:
            days_ahead = 7
        return (today + timedelta(days=days_ahead)).isoformat()

    return None


def validate_time(time_str: str) -> bool:
    """Validate that ``time_str`` is in HH:MM (24h) format."""
    if not time_str:
        return False
    return bool(re.match(r"^([01]\d|2[0-3]):([0-5]\d)$", time_str.strip()))


def validate_date(date_str: str) -> bool:
    """Validate that ``date_str`` is a valid YYYY-MM-DD date."""
    if not date_str:
        return False
    try:
        datetime.strptime(date_str.strip(), "%Y-%m-%d")
        return True
    except ValueError:
        return False


def generate_time_slots() -> list[str]:
    """Return the list of standard 1-hour business slots as HH:MM strings."""
    return [f"{hour:02d}:00" for hour in BUSINESS_HOURS]
