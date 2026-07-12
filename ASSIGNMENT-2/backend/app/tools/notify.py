"""send_booking_notification tool — performs a mock webhook trigger.

Sends an HTTP POST to the user-provided webhook URL (e.g. Webhook.site or
Pipedream) to simulate sending an email/WhatsApp confirmation. If no webhook
URL is configured, the notification is logged and a mock success is returned.
"""

from __future__ import annotations

import json
import logging

import httpx
from langchain_core.tools import tool

logger = logging.getLogger(__name__)


@tool
def send_booking_notification(email: str, details: str, webhook_url: str = "") -> dict:
    """Send a booking confirmation notification via a webhook.

    Args:
        email: The recipient's email address.
        details: A human-readable summary of the booking.
        webhook_url: The webhook endpoint to POST to. If empty, the
            notification is logged only (mock mode).

    Returns:
        A dict with ``success`` (bool), ``status_code`` (int), and
        ``message`` (str).
    """
    payload = {
        "type": "booking_confirmation",
        "email": email,
        "details": details,
    }

    if not webhook_url:
        logger.info("[MOCK NOTIFICATION] No webhook URL configured. Logging only.")
        logger.info("Notification payload: %s", json.dumps(payload, indent=2))
        return {
            "success": True,
            "status_code": 200,
            "message": "Notification logged (mock mode — no webhook URL configured).",
            "payload": payload,
        }

    try:
        response = httpx.post(
            webhook_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10.0,
        )
        if response.status_code < 400:
            return {
                "success": True,
                "status_code": response.status_code,
                "message": f"Notification sent successfully to webhook (HTTP {response.status_code}).",
                "payload": payload,
            }
        return {
            "success": False,
            "status_code": response.status_code,
            "message": f"Webhook returned error status {response.status_code}: {response.text[:200]}",
            "payload": payload,
        }
    except httpx.RequestError as exc:
        logger.error("Webhook request failed: %s", exc)
        return {
            "success": False,
            "status_code": 0,
            "message": f"Failed to reach webhook: {exc}",
            "payload": payload,
        }
