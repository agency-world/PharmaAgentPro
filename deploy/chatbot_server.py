"""PharmaAgent Pro — Web Chatbot Server.

Serves the agentic chatbot UI and proxies messages to the
deployed Claude Managed Agent on platform.claude.com.

Usage:
    python deploy/chatbot_server.py
    Open http://localhost:3000
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv

load_dotenv()

import anthropic
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from src.tools.drug_tools import DrugLookupTool, DrugInteractionTool
from src.tools.trial_tools import TrialSearchTool, AdverseEventSearchTool, SafetySignalTool
from src.tools.document_tools import DocumentGeneratorTool

DEPLOY_STATE_FILE = Path(__file__).parent / "deploy_state.json"
UI_FILE = Path(__file__).parent / "chatbot_ui.html"

TOOL_EXECUTORS = {
    "drug_lookup": lambda inp: DrugLookupTool.execute(**inp),
    "drug_interaction_check": lambda inp: DrugInteractionTool.execute(**inp),
    "trial_search": lambda inp: TrialSearchTool.execute(**inp),
    "adverse_event_search": lambda inp: AdverseEventSearchTool.execute(**inp),
    "safety_signal_analysis": lambda inp: SafetySignalTool.execute(**inp),
    "generate_document": lambda inp: DocumentGeneratorTool.execute(**inp),
}

app = FastAPI(title="PharmaAgent Pro Chatbot")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

_client: anthropic.Anthropic | None = None
_state: dict = {}


def _init():
    global _client, _state
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not set")
        _client = anthropic.Anthropic(api_key=api_key)
    # Always re-read state so we pick up session changes from other processes
    if DEPLOY_STATE_FILE.exists():
        with open(DEPLOY_STATE_FILE) as f:
            _state = json.load(f)


@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    _init()
    return UI_FILE.read_text(encoding="utf-8")


@app.get("/api/state")
async def get_state():
    _init()
    return {
        "agent_id": _state.get("agent_id", ""),
        "session_id": _state.get("session_id", ""),
        "environment_id": _state.get("environment_id", ""),
    }


@app.post("/api/chat")
async def chat(request: Request):
    """Send message to managed agent and stream response."""
    _init()
    body = await request.json()
    message = body.get("message", "")
    session_id = body.get("session_id") or _state.get("session_id")

    if not session_id:
        async def no_session_stream():
            yield f"data: {json.dumps({'type': 'error', 'content': 'No session. Deploy first: python deploy/deploy_managed_agent.py'})}\n\n"
        return StreamingResponse(no_session_stream(), media_type="text/event-stream")

    async def event_stream():
        pending_tool_results: list[dict] = []
        try:
            with _client.beta.sessions.events.stream(session_id) as stream:
                _client.beta.sessions.events.send(
                    session_id,
                    events=[
                        {
                            "type": "user.message",
                            "content": [{"type": "text", "text": message}],
                        },
                    ],
                )

                for event in stream:
                    if event.type == "agent.message":
                        for block in event.content:
                            if hasattr(block, "text"):
                                yield f"data: {json.dumps({'type': 'text', 'content': block.text})}\n\n"

                    elif event.type == "agent.thinking":
                        yield f"data: {json.dumps({'type': 'thinking', 'content': '...'})}\n\n"

                    elif event.type == "agent.tool_use":
                        yield f"data: {json.dumps({'type': 'tool', 'name': event.name})}\n\n"

                    elif event.type == "agent.custom_tool_use":
                        tool_name = event.name
                        tool_event_id = event.id
                        executor = TOOL_EXECUTORS.get(tool_name)
                        if executor:
                            try:
                                result = executor(event.input)
                            except Exception as e:
                                result = json.dumps({"error": str(e)})
                        else:
                            result = json.dumps({"error": f"Unknown tool: {tool_name}"})

                        pending_tool_results.append({
                            "event_id": tool_event_id,
                            "result": result,
                        })
                        yield f"data: {json.dumps({'type': 'tool', 'name': tool_name})}\n\n"

                    elif event.type == "session.status_idle":
                        # If session needs custom tool results, send them and continue
                        stop_reason = getattr(event, "stop_reason", None)
                        if (
                            stop_reason
                            and getattr(stop_reason, "type", None) == "requires_action"
                            and pending_tool_results
                        ):
                            for ptr in pending_tool_results:
                                _client.beta.sessions.events.send(
                                    session_id,
                                    events=[
                                        {
                                            "type": "user.custom_tool_result",
                                            "custom_tool_use_id": ptr["event_id"],
                                            "content": [{"type": "text", "text": ptr["result"]}],
                                        },
                                    ],
                                )
                            pending_tool_results.clear()
                            continue
                        yield f"data: {json.dumps({'type': 'done'})}\n\n"
                        break

                    elif event.type == "session.status_terminated":
                        yield f"data: {json.dumps({'type': 'error', 'content': 'Session terminated'})}\n\n"
                        break

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.post("/api/new-session")
async def new_session():
    """Create a new session on the managed agent."""
    _init()
    session_kwargs = {
        "agent": _state["agent_id"],
        "environment_id": _state["environment_id"],
        "title": "PharmaAgent Pro Chat",
    }
    if _state.get("memory_store_id"):
        session_kwargs["resources"] = [
            {
                "type": "memory_store",
                "memory_store_id": _state["memory_store_id"],
                "access": "read_write",
                "prompt": "Check /pharma/ for summaries and /data/ for full datasets.",
            },
        ]
    session = _client.beta.sessions.create(**session_kwargs)
    _state["session_id"] = session.id
    with open(DEPLOY_STATE_FILE, "w") as f:
        json.dump(_state, f, indent=2)
    return {"session_id": session.id}


if __name__ == "__main__":
    print("PharmaAgent Pro Chatbot Server")
    print("Open http://localhost:3000")
    uvicorn.run(app, host="0.0.0.0", port=3000)
