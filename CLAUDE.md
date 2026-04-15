# PharmaAgent Pro — Claude Managed Agent for Pharmaceutical Intelligence

## Project Overview
PharmaAgent Pro is a multi-agent pharmaceutical assistant powered by the Claude Agent SDK and the Claude Managed Agents platform. It delivers Drug Discovery, Clinical Trial Research, Regulatory Document Generation, and Safety / Pharmacovigilance capabilities behind a single orchestrator.

## Architecture
- **Framework**: Claude Agent SDK (Python) + Claude Managed Agents API
- **Models**: Opus 4.6 for complex reasoning, Sonnet 4.6 for fast specialist work, Haiku 4.5 for query classification/routing
- **Orchestration**: [src/agents/orchestrator.py](src/agents/orchestrator.py) classifies queries and dispatches to one of four domain sub-agents (`drug_discovery`, `clinical_trials`, `regulatory`, `safety`) or handles general queries directly with the full toolset.
- **Tools**: Six custom tools under [src/tools/](src/tools/) — `drug_lookup`, `drug_interaction_check`, `trial_search`, `adverse_event_search`, `safety_signal_analysis`, `generate_document`.
- **Datasets**: Local JSON curated data in [src/datasets/](src/datasets/) (compounds, trials, adverse events, regulatory templates).
- **Skills**: Sub-agent capabilities and tool mappings are documented in [SKILLS.md](SKILLS.md).
- **Memory**: Persistent store ([src/memory/memory_store.py](src/memory/memory_store.py)) for user preferences, drug context, and trial history.
- **Guardrails**: Input validation, PII redaction, output filtering, compliance checks, rate limiting ([src/guardrails/](src/guardrails/)).
- **Observability**: Per-call usage tracking and audit log ([src/utils/usage_tracker.py](src/utils/usage_tracker.py), [src/utils/audit.py](src/utils/audit.py)); all LLM calls logged to `logs/`.
- **Deployment**: Local CLI + FastAPI, or fully-managed deployment on `platform.claude.com` via [deploy/deploy_managed_agent.py](deploy/deploy_managed_agent.py) with terminal ([deploy/chatbot.py](deploy/chatbot.py)) and web ([deploy/chatbot_server.py](deploy/chatbot_server.py), [deploy/chatbot_ui.html](deploy/chatbot_ui.html)) clients.

## Key Commands
- `python -m src.main` — Launch interactive multi-turn CLI (Rich UI, slash commands)
- `python -m src.main --mode api` — Launch FastAPI server on port 8000
- `python deploy/deploy_managed_agent.py` — Provision agent/env/memory/session on `platform.claude.com`
- `python deploy/chatbot.py` — Terminal chatbot against the deployed managed agent
- `python deploy/chatbot_server.py` — Web chatbot at `http://localhost:3000`
- `pytest tests/` — Run test suite (tools, guardrails, memory, utils)
- `ruff check src/ tests/` — Lint

## CLI Slash Commands (local interactive mode)
`/help`, `/status`, `/usage`, `/audit`, `/memory <query>`, `/remember <path> <content>`, `/reset`, `/thinking on|off`, `/quit`.

## Conventions
- All pharma data stays local; never transmit patient PII to external services.
- Regulatory documents must include compliance metadata headers and are marked "requires human review before submission."
- Tools must never fabricate data — agents use only values returned by tool calls.
- All LLM calls are logged to `logs/` with token usage, latency, and audit metadata.
- Extended thinking is enabled for drug interaction analysis and safety/benefit-risk assessments.
- CTCAE v5.0 grading for adverse events; cite specific regulations (e.g., 21 CFR 312.33) in regulatory output.
- SAEs requiring expedited (15-day / 7-day) reporting must be flagged prominently.

## Files Not to Commit
See [.gitignore](.gitignore) — notably `logs/`, `deploy/deploy_state.json`, `node_modules/`, `.env`, generated `docs/*.docx|.pptx`, and `UserGuide.rtf`.
