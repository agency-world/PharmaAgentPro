# PharmaAgent Pro

Multi-agent pharmaceutical intelligence assistant powered by the **Claude Agent SDK** and the **Claude Managed Agents platform**. It combines specialized sub-agents for drug discovery, clinical trial research, regulatory document generation, and pharmacovigilance behind a single orchestrator.

---

## Features

- **Orchestrator + 4 domain sub-agents** — Drug Discovery, Clinical Trials, Regulatory Affairs, Safety/PV. Routing is classified by Haiku 4.5 and dispatched to Opus 4.6 / Sonnet 4.6.
- **6 custom pharma tools** — `drug_lookup`, `drug_interaction_check`, `trial_search`, `adverse_event_search`, `safety_signal_analysis`, `generate_document`.
- **Local curated datasets** — compounds, trials, adverse events, and regulatory templates under [src/datasets/](src/datasets/).
- **Guardrails** — input validation, PII redaction, output filtering, compliance checks, rate limiting ([src/guardrails/](src/guardrails/)).
- **Persistent memory store** — multi-turn user/drug/trial context ([src/memory/](src/memory/)).
- **Usage + audit tracking** — per-call token/cost metering and audit log ([src/utils/](src/utils/)).
- **Three deployment modes** — interactive CLI, FastAPI server, or fully-managed deployment on `platform.claude.com`.

---

## Project Layout

```
PharmaAgentPro/
├── src/
│   ├── main.py              # Interactive CLI (Rich) — /help, /status, /memory, …
│   ├── api.py               # FastAPI server
│   ├── agents/              # orchestrator.py, base_agent.py
│   ├── tools/               # drug_tools, trial_tools, document_tools
│   ├── guardrails/          # input_validator, output_filter, compliance, rate_limiter
│   ├── memory/              # memory_store.py
│   ├── datasets/            # compounds, trials, adverse_events, regulatory_templates
│   └── utils/               # config, logger, usage_tracker, audit
├── deploy/
│   ├── deploy_managed_agent.py   # Provisions agent/env/memory/session on platform.claude.com
│   ├── chatbot.py                # Terminal chatbot against the managed agent
│   ├── chatbot_server.py         # FastAPI server hosting chatbot_ui.html
│   └── chatbot_ui.html           # Single-page web chatbot
├── docs/
│   ├── DEPLOYMENT.md
│   ├── TECHNICAL_GUIDE.md
│   ├── MARKETING_DECK.md
│   └── generate_{docx,pptx}.py   # Rebuild bundled technical/marketing artifacts
├── tests/                    # pytest suite for tools, guardrails, memory, utils
├── CLAUDE.md                 # Claude Code project instructions
├── SKILLS.md                 # Skills / sub-agent capability catalog
├── requirements.txt / pyproject.toml
└── package.json              # Node deps for docx/pptx generators
```

---

## Quick Start — Local

```bash
# 1. Install Python deps
pip install -r requirements.txt

# 2. Configure API key
cp .env.example .env
echo "ANTHROPIC_API_KEY=sk-ant-..." >> .env

# 3. Run interactive chat
python -m src.main

# or launch the REST API (http://localhost:8000)
python -m src.main --mode api
```

Interactive CLI commands: `/help`, `/status`, `/usage`, `/audit`, `/memory <q>`, `/remember <path> <content>`, `/reset`, `/thinking on|off`, `/quit`.

## Quick Start — Managed Agent Deployment

```bash
export ANTHROPIC_API_KEY=sk-ant-...
python deploy/deploy_managed_agent.py      # Creates agent, env, memory, session
python deploy/chatbot.py                   # Terminal chat
# or
python deploy/chatbot_server.py            # Web chat at http://localhost:3000
```

See [deploy/README.md](deploy/README.md) and [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for details on the Managed Agent topology, custom-tool event flow, and the resources provisioned on `platform.claude.com`.

---

## Models

| Role | Model |
|------|-------|
| Primary reasoning (orchestrator, specialists) | `claude-opus-4-6` |
| Fast specialist tasks / document generation | `claude-sonnet-4-6` |
| Query classifier / routing | `claude-haiku-4-5-20251001` |

Extended thinking is enabled for drug interaction analysis and safety/benefit-risk assessments.

---

## Development

```bash
pip install -e ".[dev]"
pytest tests/
ruff check src/ tests/
```

---

## Docs

- [Technical Guide](docs/TECHNICAL_GUIDE.md) — architecture deep-dive
- [Deployment](docs/DEPLOYMENT.md) — managed agent setup
- [Skills Catalog](SKILLS.md) — sub-agent capabilities and tool mapping
- [Claude Project Instructions](CLAUDE.md) — conventions for agentic collaborators

---

## Safety & Compliance Notes

- All pharma data stays local; patient PII is never transmitted to external services.
- Regulatory documents include compliance metadata headers and require human review before submission.
- All LLM calls are logged to `logs/` with token usage and latency.
