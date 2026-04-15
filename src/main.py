"""PharmaAgent Pro — Interactive multi-turn chat agent.

Usage:
    python -m src.main                 # Interactive CLI chat
    python -m src.main --mode api      # Launch FastAPI server
"""

from __future__ import annotations

import argparse
import sys
import uuid

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from src.agents.orchestrator import PharmaOrchestrator
from src.utils.config import Config
from src.utils.logger import get_logger

logger = get_logger("main")
console = Console()

BANNER = """\
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   ██████╗ ██╗  ██╗ █████╗ ██████╗ ███╗   ███╗ █████╗        ║
║   ██╔══██╗██║  ██║██╔══██╗██╔══██╗████╗ ████║██╔══██╗       ║
║   ██████╔╝███████║███████║██████╔╝██╔████╔██║███████║       ║
║   ██╔═══╝ ██╔══██║██╔══██║██╔══██╗██║╚██╔╝██║██╔══██║       ║
║   ██║     ██║  ██║██║  ██║██║  ██║██║ ╚═╝ ██║██║  ██║       ║
║   ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝╚═╝  ╚═╝       ║
║                                                              ║
║          █████╗  ██████╗ ███████╗███╗   ██╗████████╗         ║
║         ██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝        ║
║         ███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║           ║
║         ██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║           ║
║         ██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║           ║
║         ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝           ║
║                                                              ║
║          P R O — Pharmaceutical Intelligence                 ║
║          Powered by Claude Managed Agents                    ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝"""

HELP_TEXT = """\
## Commands
| Command | Description |
|---------|-------------|
| `/help` | Show this help message |
| `/status` | Show system status (agents, usage, memory) |
| `/memory <query>` | Search the memory store |
| `/remember <path> <content>` | Save to memory store |
| `/thinking on/off` | Toggle extended thinking |
| `/reset` | Clear conversation history |
| `/usage` | Show LLM token usage summary |
| `/audit` | Show recent audit log entries |
| `/quit` | Exit the application |

## Example Queries
- "Look up compound Nexavirin and assess its drug-likeness"
- "Show me the status of the ONCOLYZE-3 Phase III trial"
- "Check for drug interactions between Inflammablock and Oncolytin-B"
- "Generate a CIOMS safety report for the Immunex-340 hepatitis SAE"
- "Run a safety signal analysis on Oncolytin-B"
- "What are the enrollment rates across all active trials?"
"""


def _display_response(result: dict) -> None:
    """Render agent response with metadata."""
    # Show thinking if present
    if result.get("thinking"):
        console.print(Panel(
            Text(result["thinking"][:500] + ("..." if len(result["thinking"]) > 500 else ""), style="dim"),
            title="[yellow]Extended Thinking[/yellow]",
            border_style="yellow",
        ))

    # Show tool calls
    if result.get("tool_calls"):
        table = Table(title="Tool Calls", show_header=True, header_style="bold cyan")
        table.add_column("Tool", style="cyan")
        table.add_column("Result Preview", style="dim")
        for tc in result["tool_calls"]:
            table.add_row(tc["tool"], tc["result_preview"][:80] + "...")
        console.print(table)

    # Show main response
    console.print()
    console.print(Markdown(result["response"]))

    # Show warnings
    for warning in result.get("warnings", []):
        console.print(f"\n[yellow]⚠ {warning}[/yellow]")

    # Show usage footer
    usage = result.get("usage", {})
    if usage:
        routing = result.get("routing", {})
        meta_parts = []
        if routing:
            meta_parts.append(f"Agent: {routing.get('agent', '?')}")
            meta_parts.append(f"Domain: {routing.get('domain', '?')}")
        meta_parts.append(f"Tokens: {usage.get('input_tokens', 0)}in/{usage.get('output_tokens', 0)}out")
        if usage.get("cache_read_tokens"):
            meta_parts.append(f"Cache: {usage['cache_read_tokens']} read")
        console.print(f"\n[dim]{'  |  '.join(meta_parts)}[/dim]")


def _handle_command(command: str, orchestrator: PharmaOrchestrator, session_id: str) -> bool:
    """Handle slash commands. Returns True if should continue loop."""
    parts = command.strip().split(maxsplit=2)
    cmd = parts[0].lower()

    if cmd == "/quit":
        console.print("\n[dim]Goodbye! Session data saved.[/dim]")
        return False

    elif cmd == "/help":
        console.print(Markdown(HELP_TEXT))

    elif cmd == "/status":
        status = orchestrator.get_status()
        console.print(Panel(
            f"Active Agents: {', '.join(status['agents_active'])}\n"
            f"Total Requests: {status['usage'].get('total_requests', 0)}\n"
            f"Total Cost: ${status['usage'].get('total_cost_usd', 0):.4f}\n"
            f"Memories Stored: {status['memory_count']}\n"
            f"Audit Records: {status['audit'].get('total_records', 0)}",
            title="[bold]System Status[/bold]",
        ))

    elif cmd == "/usage":
        summary = orchestrator.main_agent.usage_tracker.get_global_summary()
        console.print(Panel(
            f"Sessions: {summary.get('sessions', 0)}\n"
            f"Total Requests: {summary.get('total_requests', 0)}\n"
            f"Input Tokens: {summary.get('total_input_tokens', 0):,}\n"
            f"Output Tokens: {summary.get('total_output_tokens', 0):,}\n"
            f"Total Cost: ${summary.get('total_cost_usd', 0):.4f}",
            title="[bold]LLM Usage Summary[/bold]",
        ))

    elif cmd == "/audit":
        records = orchestrator.main_agent.audit.query_logs(limit=10)
        if records:
            table = Table(title="Recent Audit Log", show_header=True)
            table.add_column("Time", style="dim")
            table.add_column("Type", style="cyan")
            table.add_column("Agent")
            table.add_column("Action")
            for r in records[-10:]:
                table.add_row(
                    r["timestamp"][-19:],
                    r["event_type"],
                    r["agent"],
                    r["action"][:50],
                )
            console.print(table)
        else:
            console.print("[dim]No audit records yet.[/dim]")

    elif cmd == "/memory":
        query = parts[1] if len(parts) > 1 else "/"
        results = orchestrator.search_memory(query)
        if results:
            for mem in results:
                console.print(Panel(
                    f"Content: {mem['content'][:200]}...\n"
                    f"Tags: {', '.join(mem.get('tags', []))}",
                    title=f"[cyan]{mem['path']}[/cyan] (v{mem.get('version', 1)})",
                ))
        else:
            console.print("[dim]No memories found.[/dim]")

    elif cmd == "/remember":
        if len(parts) < 3:
            console.print("[red]Usage: /remember <path> <content>[/red]")
        else:
            mem = orchestrator.save_memory(parts[1], parts[2])
            console.print(f"[green]Memory saved: {mem['path']} (v{mem['version']})[/green]")

    elif cmd == "/reset":
        orchestrator.reset()
        console.print("[green]All conversations reset.[/green]")

    elif cmd == "/thinking":
        state = parts[1] if len(parts) > 1 else "on"
        console.print(f"[dim]Extended thinking: {state}[/dim]")

    else:
        console.print(f"[red]Unknown command: {cmd}. Type /help for available commands.[/red]")

    return True


def run_interactive() -> None:
    """Run the interactive multi-turn chat interface."""
    config = Config.load()
    errors = config.validate()
    if errors:
        console.print("[red]Configuration errors:[/red]")
        for err in errors:
            console.print(f"  [red]• {err}[/red]")
        console.print("\n[dim]Copy .env.example to .env and set your ANTHROPIC_API_KEY[/dim]")
        sys.exit(1)

    console.print(BANNER, style="bold blue")
    console.print()
    console.print(Markdown("Type your query or `/help` for commands. Multi-turn conversation is maintained."))
    console.print()

    orchestrator = PharmaOrchestrator(config)
    session_id = str(uuid.uuid4())[:8]
    console.print(f"[dim]Session: {session_id} | Model: {config.models.primary_model}[/dim]\n")

    while True:
        try:
            user_input = console.input("[bold green]You >[/bold green] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Goodbye![/dim]")
            break

        if not user_input:
            continue

        # Handle slash commands
        if user_input.startswith("/"):
            if not _handle_command(user_input, orchestrator, session_id):
                break
            continue

        # Process through orchestrator
        console.print()
        with console.status("[bold cyan]Thinking...", spinner="dots"):
            result = orchestrator.chat(
                user_message=user_input,
                session_id=session_id,
            )

        _display_response(result)
        console.print()


def run_api() -> None:
    """Launch the FastAPI server."""
    import uvicorn
    from src.api import create_app

    app = create_app()
    console.print("[bold green]Starting PharmaAgent Pro API server...[/bold green]")
    uvicorn.run(app, host="0.0.0.0", port=8000)


def main() -> None:
    parser = argparse.ArgumentParser(description="PharmaAgent Pro — Pharmaceutical Intelligence Assistant")
    parser.add_argument("--mode", choices=["chat", "api"], default="chat", help="Run mode")
    args = parser.parse_args()

    if args.mode == "api":
        run_api()
    else:
        run_interactive()


if __name__ == "__main__":
    main()
