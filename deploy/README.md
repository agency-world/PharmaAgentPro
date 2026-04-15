# PharmaAgent Pro — Deployment to Claude Managed Agents Platform

## Quick Deploy

```bash
# 1. Set your API key
export ANTHROPIC_API_KEY=sk-ant-...

# 2. Deploy agent, environment, memory store, and session
python deploy/deploy_managed_agent.py

# 3. Launch the agentic chatbot (choose one):

# Option A: Terminal chatbot
python deploy/chatbot.py

# Option B: Web chatbot UI
python deploy/chatbot_server.py
# Open http://localhost:3000
```

## What Gets Deployed

| Resource | Description |
|----------|-------------|
| **Agent** | PharmaAgent Pro with system prompt, 6 custom tools, full agent toolset |
| **Environment** | Cloud container with pandas, jinja2, rich pre-installed |
| **Memory Store** | Seeded with compound library, trial data, safety alerts, regulatory standards |
| **Session** | Ready-to-use session with memory attached |

All resources are created on `platform.claude.com/workspaces/default/agents`.

## Architecture

```
┌──────────────────────────────────┐
│  Web UI (localhost:3000)         │  ← chatbot_ui.html
│  or Terminal (chatbot.py)        │
└──────────┬───────────────────────┘
           │ SSE Stream
┌──────────▼───────────────────────┐
│  Claude Managed Agent Platform   │  ← platform.claude.com
│  ┌─────────────────────────────┐ │
│  │ PharmaAgent Pro (Agent)     │ │
│  │ Model: claude-sonnet-4-6    │ │
│  │ Tools: agent_toolset +      │ │
│  │   6 custom pharma tools     │ │
│  └──────────┬──────────────────┘ │
│             │                    │
│  ┌──────────▼──────────────────┐ │
│  │ Cloud Environment           │ │
│  │ pip: pandas, jinja2, rich   │ │
│  └─────────────────────────────┘ │
│             │                    │
│  ┌──────────▼──────────────────┐ │
│  │ Memory Store                │ │
│  │ /pharma/compounds.md        │ │
│  │ /pharma/trials.md           │ │
│  │ /pharma/safety_alerts.md    │ │
│  │ /data/compounds.json        │ │
│  │ /data/trials.json           │ │
│  │ /data/adverse_events.json   │ │
│  └─────────────────────────────┘ │
└──────────────────────────────────┘
           │ Custom Tool Calls
┌──────────▼───────────────────────┐
│  Local Tool Executors            │  ← src/tools/
│  drug_lookup, trial_search,      │
│  adverse_event_search,           │
│  safety_signal_analysis,         │
│  drug_interaction_check,         │
│  generate_document               │
└──────────────────────────────────┘
```

## Custom Tool Flow

When the managed agent calls a custom tool:
1. Agent sends `agent.custom_tool_use` event via SSE
2. Chatbot executes the tool locally using `src/tools/`
3. Chatbot sends `user.custom_tool_result` event back
4. Agent continues with the tool result

## Files

| File | Purpose |
|------|---------|
| `deploy_managed_agent.py` | Creates all resources on platform.claude.com |
| `chatbot.py` | Terminal chatbot connected to managed agent |
| `chatbot_server.py` | FastAPI server serving web chatbot UI |
| `chatbot_ui.html` | Single-page agentic chatbot frontend |
| `deploy_state.json` | Persisted resource IDs (auto-generated) |
