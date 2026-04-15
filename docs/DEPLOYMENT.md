# PharmaAgent Pro — Deployment Guide

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Configuration](#configuration)
4. [Running the Application](#running-the-application)
5. [Architecture Overview](#architecture-overview)
6. [Claude Managed Agent Features Used](#claude-managed-agent-features-used)
7. [API Reference](#api-reference)
8. [Security & Compliance](#security--compliance)
9. [Monitoring & Observability](#monitoring--observability)
10. [Troubleshooting](#troubleshooting)

---

## Prerequisites

- **Python** 3.11 or higher
- **Anthropic API Key** with access to Claude Opus 4.6, Sonnet 4.6, and Haiku 4.5
- **pip** or **uv** package manager
- **Git** for version control

## Quick Start

```bash
# 1. Clone the repository
git clone <repo-url>
cd ClaudeManagedAgentApp

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows

# 3. Install dependencies
pip install -e ".[dev]"

# 4. Configure environment
cp .env.example .env
# Edit .env and set your ANTHROPIC_API_KEY

# 5. Run tests (no API key needed for tool/guardrail tests)
pytest tests/ -v

# 6. Launch interactive chat
python -m src.main

# 7. Or launch API server
python -m src.main --mode api
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | *(required)* | Your Anthropic API key |
| `PHARMA_AGENT_ENV` | `development` | Environment name |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `MAX_TOKENS_PER_REQUEST` | `8192` | Max output tokens per LLM call |
| `THINKING_BUDGET_TOKENS` | `10000` | Token budget for extended thinking |
| `CACHE_TTL_MINUTES` | `5` | Prompt cache TTL |
| `RATE_LIMIT_PER_MINUTE` | `30` | Max requests per minute per user |
| `AUDIT_LOG_PATH` | `logs/audit.jsonl` | Path for audit log |
| `MEMORY_STORE_PATH` | `src/memory/store` | Path for persistent memory |

### Model Configuration

The system uses three Claude models strategically:

| Model | Role | Use Case |
|-------|------|----------|
| **Claude Opus 4.6** | Primary | Complex reasoning, drug analysis, safety assessment |
| **Claude Sonnet 4.6** | Fast | Quick lookups, simple queries |
| **Claude Haiku 4.5** | Classifier | Query routing, domain classification |

## Running the Application

### Interactive CLI Chat

```bash
python -m src.main
```

Features:
- Multi-turn conversation with context retention
- Automatic routing to specialized agents
- Extended thinking for complex analyses
- Slash commands: `/help`, `/status`, `/usage`, `/audit`, `/memory`, `/reset`

### API Server

```bash
python -m src.main --mode api
```

Server runs on `http://localhost:8000`. Interactive docs at `/docs`.

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -e .

EXPOSE 8000
CMD ["python", "-m", "src.main", "--mode", "api"]
```

```bash
docker build -t pharma-agent-pro .
docker run -p 8000:8000 -e ANTHROPIC_API_KEY=sk-ant-... pharma-agent-pro
```

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     User Interface                          │
│                  (CLI Chat / FastAPI)                        │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                   Guardrails Layer                           │
│  ┌──────────────┐ ┌───────────┐ ┌────────────┐ ┌─────────┐ │
│  │ Input        │ │ Output    │ │ Compliance │ │ Rate    │ │
│  │ Validator    │ │ Filter    │ │ Checker    │ │ Limiter │ │
│  │ • PII detect │ │ • PII     │ │ • FDA/ICH  │ │ • Per   │ │
│  │ • Injection  │ │   redact  │ │   rules    │ │   user  │ │
│  │ • Prohibited │ │ • Medical │ │ • Section  │ │ • Sliding│ │
│  │   topics     │ │   advice  │ │   checks   │ │   window│ │
│  └──────────────┘ └───────────┘ └────────────┘ └─────────┘ │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                  Orchestrator Agent                          │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Query Classifier (Haiku 4.5 — fast routing)          │   │
│  │ Routes to: drug_discovery | clinical_trials |        │   │
│  │            regulatory | safety | general             │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────┐┌─────────────┐┌──────────┐┌────────────┐  │
│  │ Drug        ││ Clinical    ││ Regulatory││ Safety     │  │
│  │ Discovery   ││ Trials      ││ Affairs   ││ Monitoring │  │
│  │ Agent       ││ Agent       ││ Agent     ││ Agent      │  │
│  │ (Opus 4.6)  ││ (Opus 4.6)  ││ (Opus 4.6)││ (Opus 4.6) │  │
│  │ +Thinking   ││ +Thinking   ││           ││ +Thinking  │  │
│  └──────┬──────┘└──────┬──────┘└─────┬────┘└──────┬─────┘  │
│         │              │             │            │         │
│  ┌──────▼──────────────▼─────────────▼────────────▼──────┐  │
│  │                 Tool Layer                            │  │
│  │  drug_lookup | drug_interaction_check | trial_search  │  │
│  │  adverse_event_search | safety_signal_analysis        │  │
│  │  generate_document                                    │  │
│  └───────────────────────────────────────────────────────┘  │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                Infrastructure Layer                         │
│  ┌──────────┐ ┌───────────┐ ┌──────────┐ ┌──────────────┐  │
│  │ Prompt   │ │ Memory    │ │ Audit    │ │ Usage        │  │
│  │ Caching  │ │ Store     │ │ Logger   │ │ Tracker      │  │
│  │ (5-min   │ │ (local    │ │ (JSONL   │ │ (cost, token │  │
│  │  TTL)    │ │  versioned)│ │  append) │ │  tracking)   │  │
│  └──────────┘ └───────────┘ └──────────┘ └──────────────┘  │
└─────────────────────────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                  Data Layer                                  │
│  drugs_compound_library.json | clinical_trials.json         │
│  adverse_events.json | regulatory_templates.json            │
└─────────────────────────────────────────────────────────────┘
```

## Claude Managed Agent Features Used

### 1. Multi-Model Architecture
- **Opus 4.6** for complex reasoning (drug analysis, safety assessment, benefit-risk)
- **Haiku 4.5** for fast query classification and routing
- Automatic model selection based on task complexity

### 2. Extended Thinking
- Enabled for drug discovery, clinical trials, and safety agents
- Configurable budget (default 10K tokens)
- Transparent reasoning chain visible in CLI

### 3. Prompt Caching
- System prompts cached with `cache_control: {"type": "ephemeral"}`
- 5-minute TTL for multi-turn conversations
- Up to 90% cost reduction on cached tokens
- Cache metrics tracked in usage logs

### 4. Tool Use / Function Calling
- 6 custom pharma tools with JSON Schema definitions
- Automatic tool loop (up to 10 iterations)
- Tool results fed back for synthesis
- Audit logging of every tool invocation

### 5. Skills System
- 4 domain-specific SKILL.md files in `.claude/skills/`
- Drug Discovery, Clinical Trials, Regulatory Docs, Safety Monitoring
- Loaded contextually when relevant domain is detected

### 6. Persistent Memory Store
- Local file-based store with versioning
- Write, read, search, delete operations
- Agent-specific context injection into prompts
- Version history preserved for audit trail

### 7. Guardrails
- **Input**: PII detection/redaction, prompt injection defense, prohibited topic blocking
- **Output**: PII redaction, medical advice warnings, absolute claim detection
- **Compliance**: Document completeness validation against FDA/ICH standards
- **Rate Limiting**: Per-user sliding window

### 8. Audit Logging
- Append-only JSONL audit trail
- Every query, tool call, and response logged
- Filterable by event type, agent, and time
- Supports regulatory compliance requirements

### 9. Usage Tracking
- Per-request token counting (input, output, cache)
- Cost estimation using current model pricing
- Latency measurement
- Session and global aggregation

### 10. Multi-Turn Conversation
- Full conversation history maintained per session
- Context carryover across questions
- Session management (create, reset, fork)

### 11. Sub-Agent Architecture
- Orchestrator routes to specialized domain agents
- Each sub-agent has focused tools and prompts
- Lazy initialization (agents created on demand)

### 12. Claude Commands
- Pre-built command templates in `.claude/commands/`
- `/analyze-compound`, `/trial-report`, `/safety-review`, `/generate-reg-doc`

## API Reference

### POST /chat
Send a message and get an AI response.

```json
{
  "message": "Analyze the safety profile of Oncolytin-B",
  "session_id": "abc123",
  "user_id": "user1"
}
```

Response includes: `response`, `thinking`, `tool_calls`, `usage`, `warnings`, `routing`

### GET /status
System status with active agents, usage, and audit stats.

### POST /memory/write
Save to persistent memory.

### POST /memory/search
Search memory store.

### GET /usage
LLM token usage statistics.

### GET /audit
Retrieve audit log entries.

### POST /reset
Reset conversation history.

### GET /health
Health check endpoint.

## Security & Compliance

### Data Protection
- All patient PII is detected and redacted at input and output boundaries
- No PII is transmitted to the Claude API
- Memory store is local (not cloud-synced)
- Audit log provides full traceability

### Regulatory Compliance
- Documents validated against ICH/FDA standards
- Compliance checklists generated automatically
- Confidentiality notices enforced on all regulatory documents
- SAE reporting timelines enforced (7/15 day rules)

### Access Control
- Rate limiting prevents abuse
- Prompt injection detection blocks manipulation attempts
- Prohibited topics (drug synthesis, regulatory evasion, data falsification) are blocked
- Output filtering catches medical advice and absolute claims

## Monitoring & Observability

### Log Files
| File | Content |
|------|---------|
| `logs/pharma_agent.log` | Application logs |
| `logs/audit.jsonl` | Audit trail (every action) |
| `logs/usage.jsonl` | LLM usage metrics |

### Key Metrics to Monitor
- **Token usage** per session and globally
- **Cache hit rate** (target: >50% for multi-turn)
- **Latency** per request
- **Error rate** from Claude API
- **Rate limit hits** per user
- **Safety signal alerts** from the safety agent

### Usage Dashboard
Use the `/usage` and `/audit` CLI commands or API endpoints to monitor:
```bash
# In CLI
/usage
/audit
/status
```

## Troubleshooting

### Common Issues

**"ANTHROPIC_API_KEY is not set"**
→ Copy `.env.example` to `.env` and add your key.

**Rate limit errors from Claude API**
→ Reduce `RATE_LIMIT_PER_MINUTE` or upgrade your API tier.

**Extended thinking timeout**
→ Reduce `THINKING_BUDGET_TOKENS` to 5000 for faster responses.

**Memory store not persisting**
→ Ensure `src/memory/store/` directory is writable.

### Running Tests

```bash
# All tests (no API key needed for tool/guardrail tests)
pytest tests/ -v

# Specific test file
pytest tests/test_guardrails.py -v

# With coverage
pytest tests/ --cov=src --cov-report=html
```

## Sample Queries

```
# Drug Discovery
"Look up compound Nexavirin and assess its drug-likeness"
"Compare the selectivity of Oncolytin-B vs Inflammablock"
"Check for interactions between Nexavirin and Inflammablock"

# Clinical Trials
"Show enrollment status for all Phase III trials"
"What are the interim results for ONCOLYZE-3?"
"Compare AE rates across treatment arms in PCT-2024-0156"

# Regulatory
"Generate a CIOMS safety report for the Immunex-340 hepatitis SAE"
"Create an IND annual report for Nexavirin (IND-157832)"
"Draft a protocol synopsis for a new Cardiofix-200 trial"

# Safety
"Run a safety signal analysis on Oncolytin-B"
"List all serious adverse events across all trials"
"Perform a benefit-risk assessment for Inflammablock"
```
