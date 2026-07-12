"""FastAPI application entry point.

Exposes the LangGraph scheduling workflow over a REST API with SQLite-backed
conversation persistence and user authentication (register/login).
"""

from __future__ import annotations

import logging
import uuid

import httpx
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .auth import get_current_user, login_user, logout_user, register_user
from .config import get_settings
from .db import get_user_threads, init_db, save_user_thread
from .graph import get_history, invoke_graph
from .schemas import (
    AuthResponse,
    ChatRequest,
    ChatResponse,
    HealthResponse,
    HistoryResponse,
    LoginRequest,
    LogoutResponse,
    RegisterRequest,
    ThreadResponse,
    UserThreadsResponse,
    WebhookTestRequest,
    WebhookTestResponse,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(
    title="Multi-Agent Scheduling Assistant",
    description="LangGraph-powered multi-agent calendar booking API with user authentication",
    version="2.0.0",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    """Initialize the database on application startup."""
    init_db()
    logger.info("Database initialized at startup")


# ---------------------------------------------------------------------------
# Health (public)
# ---------------------------------------------------------------------------

@app.get("/api/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint for Render."""
    return HealthResponse(status="ok", service="scheduling-assistant-api")


# ---------------------------------------------------------------------------
# Auth endpoints (public)
# ---------------------------------------------------------------------------

@app.post("/api/register", response_model=AuthResponse)
async def register(request: RegisterRequest) -> AuthResponse:
    """Register a new user account."""
    try:
        result = register_user(request.email, request.password)
        logger.info("User registered: %s", request.email)
        return AuthResponse(token=result["token"], email=result["email"])
    except ValueError as exc:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@app.post("/api/login", response_model=AuthResponse)
async def login(request: LoginRequest) -> AuthResponse:
    """Login an existing user."""
    try:
        result = login_user(request.email, request.password)
        logger.info("User logged in: %s", request.email)
        return AuthResponse(token=result["token"], email=result["email"])
    except ValueError as exc:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        )


@app.post("/api/logout", response_model=LogoutResponse)
async def logout(user: dict = Depends(get_current_user)) -> LogoutResponse:
    """Logout the current user (deletes the session)."""
    logout_user(user["token"])
    logger.info("User logged out: %s", user["email"])
    return LogoutResponse(message="Logged out successfully.")


# ---------------------------------------------------------------------------
# Authenticated endpoints
# ---------------------------------------------------------------------------

@app.post("/api/thread", response_model=ThreadResponse)
async def create_thread(user: dict = Depends(get_current_user)) -> ThreadResponse:
    """Create a new conversation thread for the authenticated user."""
    thread_id = str(uuid.uuid4())
    save_user_thread(user["email"], thread_id)
    logger.info("Created new thread %s for user %s", thread_id, user["email"])
    return ThreadResponse(thread_id=thread_id)


@app.get("/api/threads", response_model=UserThreadsResponse)
async def list_user_threads(user: dict = Depends(get_current_user)) -> UserThreadsResponse:
    """List all conversation threads for the authenticated user."""
    threads = get_user_threads(user["email"])
    return UserThreadsResponse(email=user["email"], threads=threads)


@app.post("/api/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    user: dict = Depends(get_current_user),
) -> ChatResponse:
    """Send a message to the scheduling assistant.

    The message is processed by the LangGraph state machine (Triage Agent →
    Booking Specialist). Conversation state is persisted via SqliteSaver
    keyed by thread_id. The authenticated user's email is auto-injected
    into booking tools.
    """
    logger.info(
        "Chat request from %s on thread %s: %s",
        user["email"],
        request.thread_id,
        request.message[:100],
    )

    try:
        result = invoke_graph(
            thread_id=request.thread_id,
            message=request.message,
            webhook_url=request.webhook_url,
            user_email=user["email"],
        )

        # Extract the last AI message as the reply
        messages = result.get("messages", [])
        reply = ""
        for msg in reversed(messages):
            if msg.type == "ai":
                reply = msg.content if isinstance(msg.content, str) else str(msg.content)
                break

        pending_booking = result.get("pending_booking")

        return ChatResponse(
            thread_id=request.thread_id,
            reply=reply,
            pending_booking=pending_booking,
        )
    except Exception as exc:
        logger.exception("Error processing chat request")
        return ChatResponse(
            thread_id=request.thread_id,
            reply=f"I apologize, but an error occurred while processing your request: {exc}",
            pending_booking=None,
        )


@app.get("/api/history/{thread_id}", response_model=HistoryResponse)
async def get_thread_history(
    thread_id: str,
    user: dict = Depends(get_current_user),
) -> HistoryResponse:
    """Retrieve the conversation history for a thread.

    Only returns history if the thread belongs to the authenticated user.
    """
    # Verify the thread belongs to this user
    user_threads = get_user_threads(user["email"])
    if thread_id not in user_threads:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this conversation.",
        )

    messages = get_history(thread_id)
    return HistoryResponse(thread_id=thread_id, messages=messages)


@app.post("/api/test-webhook", response_model=WebhookTestResponse)
async def test_webhook(
    request: WebhookTestRequest,
    user: dict = Depends(get_current_user),
) -> WebhookTestResponse:
    """Test a webhook URL by sending a test payload."""
    payload = {
        "type": "webhook_test",
        "message": "This is a test notification from the Scheduling Assistant.",
        "user": user["email"],
    }

    try:
        response = httpx.post(
            request.webhook_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10.0,
        )
        if response.status_code < 400:
            return WebhookTestResponse(
                success=True,
                message=f"Webhook test successful (HTTP {response.status_code}).",
                status_code=response.status_code,
            )
        return WebhookTestResponse(
            success=False,
            message=f"Webhook returned error status {response.status_code}.",
            status_code=response.status_code,
        )
    except httpx.RequestError as exc:
        return WebhookTestResponse(
            success=False,
            message=f"Failed to reach webhook: {exc}",
            status_code=0,
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
