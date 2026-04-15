"""PharmaAgent Pro — Terminal Chatbot using Claude Managed Agents.

This connects to the deployed managed agent on platform.claude.com
and provides a multi-turn agentic chat experience.

Usage:
    python deploy/chatbot.py
    python deploy/chatbot.py --session <session_id>  # Resume session
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv

load_dotenv()

import anthropic
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text

from src.tools.drug_tools import DrugLookupTool, DrugInteractionTool
from src.tools.trial_tools import TrialSearchTool, AdverseEventSearchTool, SafetySignalTool
from src.tools.document_tools import DocumentGeneratorTool

console = Console()

DEPLOY_STATE_FILE = Path(__file__).parent / "deploy_state.json"

# Map custom tool names to local executors
TOOL_EXECUTORS = {
    "drug_lookup": lambda inp: DrugLookupTool.execute(**inp),
    "drug_interaction_check": lambda inp: DrugInteractionTool.execute(**inp),
    "trial_search": lambda inp: TrialSearchTool.execute(**inp),
    "adverse_event_search": lambda inp: AdverseEventSearchTool.execute(**inp),
    "safety_signal_analysis": lambda inp: SafetySignalTool.execute(**inp),
    "generate_document": lambda inp: DocumentGeneratorTool.execute(**inp),
}


def load_deploy_state() -> dict:
    if not DEPLOY_STATE_FILE.exists():
        console.print("[red]No deployment state found. Run deploy first:[/red]")
        console.print("  python deploy/deploy_managed_agent.py")
        sys.exit(1)
    with open(DEPLOY_STATE_FILE, "r") as f:
        return json.load(f)


def run_chatbot(session_id: str | None = None) -> None:
    """Run the interactive managed agent chatbot."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        console.print("[red]ANTHROPIC_API_KEY not set[/red]")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    state = load_deploy_state()

    # Use provided session or create new one
    if session_id:
        sid = session_id
    elif "session_id" in state:
        sid = state["session_id"]
    else:
        console.print("[yellow]Creating new session...[/yellow]")
        session_kwargs = {
            "agent": state["agent_id"],
            "environment_id": state["environment_id"],
            "title": "PharmaAgent Pro Chat",
        }
        if state.get("memory_store_id"):
            session_kwargs["resources"] = [
                {
                    "type": "memory_store",
                    "memory_store_id": state["memory_store_id"],
                    "access": "read_write",
                    "prompt": "Check /pharma/ for summaries and /data/ for full datasets.",
                },
            ]
        session = client.beta.sessions.create(**session_kwargs)
        sid = session.id
        state["session_id"] = sid
        with open(DEPLOY_STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)

    console.print(Panel(
        "[bold blue]PharmaAgent Pro[/bold blue] — Managed Agent Chatbot\n"
        f"Session: [cyan]{sid}[/cyan]\n"
        f"Agent: [cyan]{state.get('agent_id', 'unknown')}[/cyan]\n\n"
        "Type your query or 'quit' to exit.",
        title="Connected to platform.claude.com",
        border_style="blue",
    ))

    while True:
        try:
            user_input = console.input("\n[bold green]You >[/bold green] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Goodbye![/dim]")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "/quit"):
            console.print("[dim]Goodbye![/dim]")
            break

        # Send message and stream response
        console.print()
        pending_tool_results: list[dict] = []
        try:
            with client.beta.sessions.events.stream(sid) as stream:
                # Send user message
                client.beta.sessions.events.send(
                    sid,
                    events=[
                        {
                            "type": "user.message",
                            "content": [{"type": "text", "text": user_input}],
                        },
                    ],
                )

                # Process streaming events
                response_text = ""
                for event in stream:
                    if event.type == "agent.message":
                        for block in event.content:
                            if hasattr(block, "text"):
                                response_text += block.text
                                console.print(block.text, end="", markup=False)

                    elif event.type == "agent.thinking":
                        console.print("[dim]  (thinking...)[/dim]")

                    elif event.type == "agent.tool_use":
                        console.print(f"\n[cyan]  Tool: {event.name}[/cyan]")

                    elif event.type == "agent.custom_tool_use":
                        # Execute custom tool locally and send result back
                        tool_name = event.name
                        tool_input = event.input
                        tool_event_id = event.id
                        console.print(f"\n[cyan]  Custom Tool: {tool_name}[/cyan]")

                        executor = TOOL_EXECUTORS.get(tool_name)
                        if executor:
                            try:
                                result = executor(tool_input)
                            except Exception as e:
                                result = json.dumps({"error": str(e)})
                        else:
                            result = json.dumps({"error": f"Unknown tool: {tool_name}"})

                        # Store pending tool result — send after session goes idle
                        pending_tool_results.append({
                            "event_id": tool_event_id,
                            "result": result,
                        })

                    elif event.type == "session.status_idle":
                        # Check if session is waiting for custom tool results
                        stop_reason = getattr(event, "stop_reason", None)
                        if (
                            stop_reason
                            and getattr(stop_reason, "type", None) == "requires_action"
                            and pending_tool_results
                        ):
                            # Send all pending tool results back
                            for ptr in pending_tool_results:
                                client.beta.sessions.events.send(
                                    sid,
                                    events=[
                                        {
                                            "type": "user.custom_tool_result",
                                            "custom_tool_use_id": ptr["event_id"],
                                            "content": [{"type": "text", "text": ptr["result"]}],
                                        },
                                    ],
                                )
                            pending_tool_results.clear()
                            # Continue streaming — agent will process tool results
                            continue
                        break

                    elif event.type == "session.status_terminated":
                        console.print("\n[red]Session terminated unexpectedly.[/red]")
                        break

                    elif event.type == "session.error":
                        console.print(f"\n[red]Error: {event}[/red]")

                console.print()  # Final newline

        except anthropic.APIError as e:
            console.print(f"\n[red]API Error: {e}[/red]")
        except Exception as e:
            console.print(f"\n[red]Error: {e}[/red]")


def main():
    parser = argparse.ArgumentParser(description="PharmaAgent Pro Managed Agent Chatbot")
    parser.add_argument("--session", type=str, default=None, help="Resume specific session ID")
    args = parser.parse_args()
    run_chatbot(session_id=args.session)


if __name__ == "__main__":
    main()
