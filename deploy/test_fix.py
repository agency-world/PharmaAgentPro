"""Quick non-interactive test to verify the custom tool result fix."""
from __future__ import annotations
import json, os, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv()

import anthropic
from src.tools.drug_tools import DrugLookupTool, DrugInteractionTool
from src.tools.trial_tools import TrialSearchTool, AdverseEventSearchTool, SafetySignalTool
from src.tools.document_tools import DocumentGeneratorTool

TOOL_EXECUTORS = {
    "drug_lookup": lambda inp: DrugLookupTool.execute(**inp),
    "drug_interaction_check": lambda inp: DrugInteractionTool.execute(**inp),
    "trial_search": lambda inp: TrialSearchTool.execute(**inp),
    "adverse_event_search": lambda inp: AdverseEventSearchTool.execute(**inp),
    "safety_signal_analysis": lambda inp: SafetySignalTool.execute(**inp),
    "generate_document": lambda inp: DocumentGeneratorTool.execute(**inp),
}

DEPLOY_STATE_FILE = Path(__file__).parent / "deploy_state.json"

def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    with open(DEPLOY_STATE_FILE) as f:
        state = json.load(f)

    # Create a fresh session to avoid any stale state
    print("Creating fresh session...")
    session_kwargs = {
        "agent": state["agent_id"],
        "environment_id": state["environment_id"],
        "title": "PharmaAgent Pro — Fix Test",
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
    print(f"Session: {sid}")

    # Update deploy state with new session
    state["session_id"] = sid
    with open(DEPLOY_STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

    # Send test query
    test_query = "Which compounds target EGFR?"
    print(f"\nSending: {test_query}")
    print("-" * 50)

    pending_tool_results: list[dict] = []

    with client.beta.sessions.events.stream(sid) as stream:
        client.beta.sessions.events.send(
            sid,
            events=[
                {
                    "type": "user.message",
                    "content": [{"type": "text", "text": test_query}],
                },
            ],
        )

        for event in stream:
            if event.type == "agent.message":
                for block in event.content:
                    if hasattr(block, "text"):
                        print(block.text, end="")

            elif event.type == "agent.thinking":
                print("  (thinking...)")

            elif event.type == "agent.tool_use":
                print(f"\n  [Built-in Tool: {event.name}]")

            elif event.type == "agent.custom_tool_use":
                tool_name = event.name
                tool_event_id = event.id
                print(f"\n  [Custom Tool: {tool_name}] id={tool_event_id}")

                executor = TOOL_EXECUTORS.get(tool_name)
                if executor:
                    try:
                        result = executor(event.input)
                        print(f"  -> Result length: {len(result)} chars")
                    except Exception as e:
                        result = json.dumps({"error": str(e)})
                        print(f"  -> Error: {e}")
                else:
                    result = json.dumps({"error": f"Unknown tool: {tool_name}"})

                pending_tool_results.append({
                    "event_id": tool_event_id,
                    "result": result,
                })

            elif event.type == "session.status_idle":
                stop_reason = getattr(event, "stop_reason", None)
                sr_type = getattr(stop_reason, "type", None) if stop_reason else None
                print(f"\n  [Session idle, stop_reason={sr_type}]")

                if sr_type == "requires_action" and pending_tool_results:
                    print(f"  Sending {len(pending_tool_results)} tool result(s)...")
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
                        print(f"    Sent result for {ptr['event_id']}")
                    pending_tool_results.clear()
                    continue
                print("\n" + "=" * 50)
                print("DONE - Fix works!")
                break

            elif event.type == "session.status_terminated":
                print("\n[Session terminated]")
                break

            elif event.type == "session.error":
                print(f"\n[Error: {event}]")

    print()

if __name__ == "__main__":
    main()
