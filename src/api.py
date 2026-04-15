"""FastAPI server for PharmaAgent Pro — REST API for the agent system."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.agents.orchestrator import PharmaOrchestrator
from src.utils.config import Config
from src.utils.logger import get_logger

logger = get_logger("api")


# --- Request / Response Models ---

class ChatRequest(BaseModel):
    """Request body for the chat endpoint."""
    message: str = Field(..., min_length=1, max_length=50000, description="User message")
    session_id: str = Field(default="", description="Session ID for multi-turn conversations")
    user_id: str = Field(default="default", description="User identifier for rate limiting")


class ChatResponse(BaseModel):
    """Response body from the chat endpoint."""
    response: str
    thinking: str | None = None
    tool_calls: list[dict[str, Any]] = []
    usage: dict[str, Any] = {}
    warnings: list[str] = []
    routing: dict[str, Any] = {}
    session_id: str = ""


class MemoryWriteRequest(BaseModel):
    """Request body for saving a memory."""
    path: str = Field(..., description="Memory path, e.g. /drugs/nexavirin/notes")
    content: str = Field(..., min_length=1, max_length=102400)
    tags: list[str] = Field(default_factory=list)


class MemorySearchRequest(BaseModel):
    """Request body for searching memories."""
    query: str = Field(..., min_length=1)
    tags: list[str] = Field(default_factory=list)
    limit: int = Field(default=10, ge=1, le=100)


class StatusResponse(BaseModel):
    """System status response."""
    agents_active: list[str]
    usage: dict[str, Any]
    audit: dict[str, Any]
    memory_count: int
    rate_limit: dict[str, Any]


# --- Session store ---
_sessions: dict[str, PharmaOrchestrator] = {}


def _get_orchestrator(session_id: str) -> tuple[PharmaOrchestrator, str]:
    """Get or create an orchestrator for the given session."""
    if not session_id:
        session_id = str(uuid.uuid4())[:8]
    if session_id not in _sessions:
        config = Config.load()
        errors = config.validate()
        if errors:
            raise HTTPException(status_code=500, detail=f"Configuration error: {'; '.join(errors)}")
        _sessions[session_id] = PharmaOrchestrator(config)
    return _sessions[session_id], session_id


# --- App factory ---

def create_app() -> FastAPI:
    """Create the FastAPI application."""
    app = FastAPI(
        title="PharmaAgent Pro API",
        description=(
            "Multi-agent pharmaceutical intelligence assistant powered by Claude Managed Agents. "
            "Provides Drug Discovery, Clinical Trials Research, Regulatory Document Generation, "
            "and Safety Monitoring capabilities."
        ),
        version="1.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health_check() -> dict[str, str]:
        return {"status": "healthy", "service": "PharmaAgent Pro"}

    @app.post("/chat", response_model=ChatResponse)
    async def chat(request: ChatRequest) -> ChatResponse:
        """Send a message to PharmaAgent Pro and get a response.

        Supports multi-turn conversations via session_id.
        The agent automatically routes to the appropriate specialist
        (drug discovery, clinical trials, regulatory, or safety).
        """
        orchestrator, session_id = _get_orchestrator(request.session_id)

        result = orchestrator.chat(
            user_message=request.message,
            session_id=session_id,
            user_id=request.user_id,
        )

        return ChatResponse(
            response=result["response"],
            thinking=result.get("thinking"),
            tool_calls=result.get("tool_calls", []),
            usage=result.get("usage", {}),
            warnings=result.get("warnings", []),
            routing=result.get("routing", {}),
            session_id=session_id,
        )

    @app.get("/status", response_model=StatusResponse)
    async def status(session_id: str = "") -> StatusResponse:
        """Get system status including active agents, usage, and audit stats."""
        orchestrator, _ = _get_orchestrator(session_id or "status")
        s = orchestrator.get_status()
        return StatusResponse(**s)

    @app.post("/memory/write")
    async def memory_write(request: MemoryWriteRequest, session_id: str = "default") -> dict[str, Any]:
        """Save information to the persistent memory store."""
        orchestrator, _ = _get_orchestrator(session_id)
        return orchestrator.save_memory(request.path, request.content, request.tags)

    @app.post("/memory/search")
    async def memory_search(request: MemorySearchRequest, session_id: str = "default") -> list[dict[str, Any]]:
        """Search the persistent memory store."""
        orchestrator, _ = _get_orchestrator(session_id)
        return orchestrator.search_memory(request.query)

    @app.post("/reset")
    async def reset(session_id: str = "") -> dict[str, str]:
        """Reset conversation history for a session."""
        if session_id and session_id in _sessions:
            _sessions[session_id].reset()
            return {"status": "reset", "session_id": session_id}
        return {"status": "no_session", "session_id": session_id}

    @app.get("/usage")
    async def usage(session_id: str = "default") -> dict[str, Any]:
        """Get LLM usage statistics."""
        orchestrator, _ = _get_orchestrator(session_id)
        return orchestrator.main_agent.usage_tracker.get_global_summary()

    @app.get("/audit")
    async def audit_log(limit: int = 50, event_type: str = "") -> list[dict[str, Any]]:
        """Retrieve audit log entries."""
        orchestrator, _ = _get_orchestrator("audit")
        return orchestrator.main_agent.audit.query_logs(
            event_type=event_type or None,
            limit=limit,
        )

    logger.info("FastAPI app created with all endpoints")
    return app
