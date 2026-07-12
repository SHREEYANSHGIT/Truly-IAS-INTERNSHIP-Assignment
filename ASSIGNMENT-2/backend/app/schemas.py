"""Pydantic request/response schemas for the FastAPI API."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Auth schemas
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    """Request body for POST /api/register."""

    email: str = Field(..., description="User email address")
    password: str = Field(..., min_length=6, description="Password (min 6 chars)")


class LoginRequest(BaseModel):
    """Request body for POST /api/login."""

    email: str = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class AuthResponse(BaseModel):
    """Response body for /api/register and /api/login."""

    token: str
    email: str


class LogoutResponse(BaseModel):
    """Response body for POST /api/logout."""

    message: str


class UserThreadsResponse(BaseModel):
    """Response body for GET /api/threads."""

    email: str
    threads: list[str]


# ---------------------------------------------------------------------------
# Chat schemas
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    """Request body for POST /api/chat."""

    thread_id: str = Field(..., description="Unique conversation thread ID")
    message: str = Field(..., description="The user's message")
    webhook_url: Optional[str] = Field(None, description="User-provided webhook URL for notifications")


class ChatResponse(BaseModel):
    """Response body for POST /api/chat."""

    thread_id: str
    reply: str
    pending_booking: Optional[dict] = None


class HistoryResponse(BaseModel):
    """Response body for GET /api/history/{thread_id}."""

    thread_id: str
    messages: list[dict]


class ThreadResponse(BaseModel):
    """Response body for POST /api/thread."""

    thread_id: str


class HealthResponse(BaseModel):
    """Response body for GET /api/health."""

    status: str
    service: str


class WebhookTestRequest(BaseModel):
    """Request body for POST /api/test-webhook."""

    webhook_url: str = Field(..., description="The webhook URL to test")


class WebhookTestResponse(BaseModel):
    """Response body for POST /api/test-webhook."""

    success: bool
    message: str
    status_code: Optional[int] = None
