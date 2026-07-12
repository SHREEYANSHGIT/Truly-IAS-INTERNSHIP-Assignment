"""SQLite database layer for slot storage and user authentication.

Initializes the ``slots``, ``users``, and ``sessions`` tables, seeds mock-taken
slots on first run, and provides helper functions used by the booking tools
and auth module.
"""

from __future__ import annotations

import os
import secrets
import sqlite3
from datetime import date, timedelta
from threading import Lock

from .config import get_settings
from .utils import generate_time_slots

_lock = Lock()
_db_path: str | None = None


def get_db_path() -> str:
    """Return the resolved SQLite database file path."""
    global _db_path
    if _db_path is None:
        settings = get_settings()
        db_path = settings.database_url
        # Ensure the parent directory exists
        parent = os.path.dirname(db_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        _db_path = db_path
    return _db_path


def get_connection() -> sqlite3.Connection:
    """Return a SQLite connection with row factory enabled."""
    conn = sqlite3.connect(get_db_path(), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create all tables and seed mock data if empty."""
    with _lock:
        conn = get_connection()
        try:
            # Users table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
                """
            )

            # Sessions table (simple token-based auth)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    token TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    email TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
                """
            )

            # Slots table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS slots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    time TEXT NOT NULL,
                    email TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    UNIQUE(date, time)
                )
                """
            )

            # User threads table (maps threads to users for per-user history)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS user_threads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_email TEXT NOT NULL,
                    thread_id TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
                """
            )

            conn.commit()

            # Seed mock-taken slots if the table is empty
            count = conn.execute("SELECT COUNT(*) FROM slots").fetchone()[0]
            if count == 0:
                _seed_mock_data(conn)
        finally:
            conn.close()


def _seed_mock_data(conn: sqlite3.Connection) -> None:
    """Pre-populate a few taken slots so negotiation is demonstrable."""
    today = date.today()
    # Seed slots for today, tomorrow, and the day after
    for offset in (0, 1, 2):
        target = today + timedelta(days=offset)
        date_str = target.isoformat()
        # Take the 10:00 and 14:00 slots on each seeded day
        for time_str in ("10:00", "14:00"):
            conn.execute(
                "INSERT OR IGNORE INTO slots (date, time, email) VALUES (?, ?, ?)",
                (date_str, time_str, "mock@example.com"),
            )
    conn.commit()


# ---------------------------------------------------------------------------
# User management
# ---------------------------------------------------------------------------

def create_user(email: str, password_hash: str, salt: str) -> bool:
    """Insert a new user. Returns True on success, False if email exists."""
    with _lock:
        conn = get_connection()
        try:
            conn.execute(
                "INSERT INTO users (email, password_hash, salt) VALUES (?, ?, ?)",
                (email.lower(), password_hash, salt),
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()


def get_user_by_email(email: str) -> dict | None:
    """Return user row as dict, or None if not found."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM users WHERE email = ?", (email.lower(),)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Session management
# ---------------------------------------------------------------------------

def create_session(user_id: int, email: str) -> str:
    """Create a session token for a user and return the token."""
    token = secrets.token_urlsafe(32)
    with _lock:
        conn = get_connection()
        try:
            conn.execute(
                "INSERT INTO sessions (token, user_id, email) VALUES (?, ?, ?)",
                (token, user_id, email.lower()),
            )
            conn.commit()
        finally:
            conn.close()
    return token


def get_session(token: str) -> dict | None:
    """Return session row as dict, or None if token is invalid."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM sessions WHERE token = ?", (token,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def delete_session(token: str) -> None:
    """Delete a session (logout)."""
    with _lock:
        conn = get_connection()
        try:
            conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
            conn.commit()
        finally:
            conn.close()


# ---------------------------------------------------------------------------
# Thread management (per-user)
# ---------------------------------------------------------------------------

def save_user_thread(user_email: str, thread_id: str) -> None:
    """Associate a thread with a user email."""
    with _lock:
        conn = get_connection()
        try:
            conn.execute(
                "INSERT OR IGNORE INTO user_threads (user_email, thread_id) VALUES (?, ?)",
                (user_email.lower(), thread_id),
            )
            conn.commit()
        finally:
            conn.close()


def get_user_threads(user_email: str) -> list[str]:
    """Return all thread IDs for a given user email."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT thread_id FROM user_threads WHERE user_email = ? ORDER BY created_at DESC",
            (user_email.lower(),),
        ).fetchall()
        return [row["thread_id"] for row in rows]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Slot management
# ---------------------------------------------------------------------------

def get_taken_slots(date_str: str) -> list[str]:
    """Return the list of taken time slots (HH:MM) for a given date."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT time FROM slots WHERE date = ? ORDER BY time", (date_str,)
        ).fetchall()
        return [row["time"] for row in rows]
    finally:
        conn.close()


def get_free_slots(date_str: str) -> list[str]:
    """Return the list of free time slots (HH:MM) for a given date."""
    taken = set(get_taken_slots(date_str))
    return [s for s in generate_time_slots() if s not in taken]


def is_slot_available(date_str: str, time_str: str) -> bool:
    """Check whether a specific date/time slot is available."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT 1 FROM slots WHERE date = ? AND time = ?",
            (date_str, time_str),
        ).fetchone()
        return row is None
    finally:
        conn.close()


def insert_slot(date_str: str, time_str: str, email: str) -> bool:
    """Insert a booking. Returns True on success, False if slot is taken."""
    with _lock:
        conn = get_connection()
        try:
            conn.execute(
                "INSERT INTO slots (date, time, email) VALUES (?, ?, ?)",
                (date_str, time_str, email),
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            # UNIQUE(date, time) constraint violated — slot already taken
            return False
        finally:
            conn.close()


def get_all_slots() -> list[dict]:
    """Return all booked slots (for debugging/admin)."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT date, time, email, created_at FROM slots ORDER BY date, time"
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def cancel_slot(date_str: str, time_str: str, email: str) -> dict:
    """Cancel (delete) a booking.

    Only deletes the slot if it belongs to the given email.
    Returns a dict with ``success`` and a ``message``.
    """
    with _lock:
        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT email FROM slots WHERE date = ? AND time = ?",
                (date_str, time_str),
            ).fetchone()
            if row is None:
                return {"success": False, "message": f"No booking found for {date_str} at {time_str}."}
            if row["email"] != email:
                return {"success": False, "message": "This booking does not belong to your account."}
            conn.execute(
                "DELETE FROM slots WHERE date = ? AND time = ? AND email = ?",
                (date_str, time_str, email),
            )
            conn.commit()
            return {
                "success": True,
                "message": f"Booking on {date_str} at {time_str} has been cancelled.",
                "cancelled": {"date": date_str, "time": time_str},
            }
        finally:
            conn.close()


def reschedule_slot(
    old_date: str,
    old_time: str,
    new_date: str,
    new_time: str,
    email: str,
) -> dict:
    """Reschedule a booking to a new date/time atomically.

    Cancels the old slot and reserves the new one in a single transaction.
    If the new slot is already taken, the old booking is preserved.
    Returns a dict with ``success`` and a ``message``.
    """
    with _lock:
        conn = get_connection()
        try:
            # Verify the old booking exists and belongs to the user
            old_row = conn.execute(
                "SELECT email FROM slots WHERE date = ? AND time = ?",
                (old_date, old_time),
            ).fetchone()
            if old_row is None:
                return {"success": False, "message": f"No booking found for {old_date} at {old_time}."}
            if old_row["email"] != email:
                return {"success": False, "message": "This booking does not belong to your account."}

            # Check the new slot is available
            new_exists = conn.execute(
                "SELECT 1 FROM slots WHERE date = ? AND time = ?",
                (new_date, new_time),
            ).fetchone()
            if new_exists is not None:
                return {
                    "success": False,
                    "message": f"The new slot ({new_date} at {new_time}) is already taken. Your original booking is unchanged.",
                }

            # Delete old and insert new atomically
            conn.execute(
                "DELETE FROM slots WHERE date = ? AND time = ? AND email = ?",
                (old_date, old_time, email),
            )
            conn.execute(
                "INSERT INTO slots (date, time, email) VALUES (?, ?, ?)",
                (new_date, new_time, email),
            )
            conn.commit()
            return {
                "success": True,
                "message": f"Booking rescheduled from {old_date} at {old_time} to {new_date} at {new_time}.",
                "booking": {"date": new_date, "time": new_time, "email": email},
            }
        except sqlite3.IntegrityError:
            conn.rollback()
            return {"success": False, "message": "The new slot is already taken. Your original booking is unchanged."}
        finally:
            conn.close()
