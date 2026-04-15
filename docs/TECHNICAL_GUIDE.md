# PharmaAgent Pro -- Technical Guide

## Product Design, Development & Deployment

**Version**: 1.0 | **Date**: April 2026 | **Classification**: Internal Technical Documentation

---

## Table of Contents

1. [Product Overview](#1-product-overview)
2. [System Architecture](#2-system-architecture)
3. [Agent Engineering & Configuration](#3-agent-engineering--configuration)
4. [Tool System Design](#4-tool-system-design)
5. [LLM Strategy & Data Retrieval](#5-llm-strategy--data-retrieval)
6. [Environment & Session Management](#6-environment--session-management)
7. [Multi-Turn Conversation & Reuse](#7-multi-turn-conversation--reuse)
8. [Guardrails & Compliance](#8-guardrails--compliance)
9. [Development Process](#9-development-process)
10. [Deployment Process](#10-deployment-process)
11. [Process Flow Diagrams](#11-process-flow-diagrams)
12. [FAQ & Troubleshooting](#12-faq--troubleshooting)
13. [Roadmap](#13-roadmap)

---

## 1. Product Overview

### What is PharmaAgent Pro?

PharmaAgent Pro is a multi-agent pharmaceutical intelligence platform built on Claude's Managed Agent SDK. It serves pharmaceutical researchers, clinicians, and regulatory professionals with four core capabilities:

| Domain | Capability | Key Functions |
|--------|-----------|---------------|
| **Drug Discovery** | Compound analysis | Drug-likeness (Lipinski), ADMET profiling, CYP interactions, SAR analysis |
| **Clinical Trials** | Trial intelligence | Trial status, enrollment tracking, endpoint analysis, interim results |
| **Regulatory Affairs** | Document generation | IND reports, CSRs, CIOMS, DSURs, IBs -- FDA/ICH compliant |
| **Safety Monitoring** | Pharmacovigilance | AE analysis, signal detection, benefit-risk assessment, SAE triage |

### Design Principles

1. **Safety First** -- PII redaction, prompt injection defense, compliance validation at every boundary
2. **Transparent Reasoning** -- Extended thinking exposes Claude's reasoning chain for complex analyses
3. **Cost Efficiency** -- Multi-model routing + prompt caching reduces LLM costs by 60-80%
4. **Auditability** -- Every query, tool call, and response is logged in an immutable audit trail
5. **Domain Fidelity** -- Pharma-specific tools, skill files, and guardrails ensure accurate, compliant outputs

---

## 2. System Architecture

### High-Level Architecture

```
                           +---------------------+
                           |    User Interfaces   |
                           | CLI | Web UI | API   |
                           +----------+----------+
                                      |
                    +-----------------v-----------------+
                    |         Guardrails Layer           |
                    | Input Validator | Rate Limiter     |
                    | PII Detection   | Injection Defense|
                    +-----------------+-----------------+
                                      |
                    +-----------------v-----------------+
                    |      PharmaOrchestrator            |
                    |  Query Classifier (Haiku 4.5)      |
                    |  confidence >= 0.7 -> sub-agent    |
                    |  confidence <  0.7 -> main agent   |
                    +-+------+------+------+-----------+
                      |      |      |      |
               +------v+ +---v--+ +v-----+ +v---------+
               | Drug   | |Trial | |Reg   | |Safety    |
               |Discovery| |Agent | |Agent | |Agent     |
               |Opus 4.6| |Opus  | |Opus  | |Opus 4.6  |
               |+Think  | |+Think| |      | |+Think    |
               +---+----+ +--+---+ +--+---+ +----+----+
                   |         |        |           |
               +---v---------v--------v-----------v----+
               |           Tool Layer                   |
               | drug_lookup | drug_interaction_check   |
               | trial_search | adverse_event_search    |
               | safety_signal_analysis                 |
               | generate_document                      |
               +---+-----------------------------------+
                   |
               +---v-----------------------------------+
               |        Infrastructure Layer            |
               | Prompt Cache | Memory Store | Audit    |
               | (5-min TTL)  | (versioned)  | (JSONL)  |
               | Usage Tracker| Config       | Logger   |
               +---------------------------------------+
                   |
               +---v-----------------------------------+
               |          Data Layer                    |
               | drugs_compound_library.json            |
               | clinical_trials.json                   |
               | adverse_events.json                    |
               | regulatory_templates.json              |
               +---------------------------------------+
```

### Directory Structure

```
ClaudeManagedAgentApp/
+-- src/
|   +-- main.py                      # CLI + FastAPI entry point
|   +-- api.py                       # REST API server (port 8000)
|   +-- agents/
|   |   +-- orchestrator.py          # Query routing via Haiku classifier
|   |   +-- base_agent.py            # Core LLM logic, tool loop, caching
|   +-- tools/
|   |   +-- drug_tools.py            # DrugLookupTool, DrugInteractionTool
|   |   +-- trial_tools.py           # TrialSearchTool, AdverseEventSearchTool, SafetySignalTool
|   |   +-- document_tools.py        # DocumentGeneratorTool
|   +-- guardrails/
|   |   +-- input_validator.py       # PII, injection, prohibited topics
|   |   +-- output_filter.py         # PII redaction, medical advice warnings
|   |   +-- compliance.py            # FDA/ICH document validation
|   |   +-- rate_limiter.py          # Per-user sliding window
|   +-- memory/
|   |   +-- memory_store.py          # Versioned local file-based store
|   +-- utils/
|   |   +-- config.py                # Environment-based configuration
|   |   +-- logger.py                # Structured logging (console + file)
|   |   +-- audit.py                 # Append-only JSONL audit trail
|   |   +-- usage_tracker.py         # Token counting, cost estimation
|   +-- datasets/                    # 4 JSON pharma datasets
+-- .claude/
|   +-- skills/                      # 4 domain SKILL.md files
|   +-- commands/                    # 4 slash command templates
+-- deploy/
|   +-- deploy_managed_agent.py      # Platform deployment script
|   +-- chatbot.py                   # Terminal chatbot (managed agent)
|   +-- chatbot_server.py            # Web chatbot server (FastAPI + SSE)
|   +-- chatbot_ui.html              # Web chatbot frontend
|   +-- deploy_state.json            # Persisted deployment resource IDs
+-- tests/                           # 71+ tests across 4 test files
+-- docs/                            # This documentation
```

---

## 3. Agent Engineering & Configuration

### 3.1 Multi-Model Strategy

PharmaAgent Pro uses three Claude models, each selected for a specific role:

| Model | Role | Why This Model | Where Used |
|-------|------|---------------|------------|
| **Claude Opus 4.6** | Primary reasoning | Deepest reasoning for drug analysis, safety assessment, benefit-risk evaluation | All 4 sub-agents |
| **Claude Haiku 4.5** | Query classifier | Fastest model for real-time routing decisions (~100ms) | Orchestrator classifier |
| **Claude Sonnet 4.6** | Managed Agent model | Balanced cost/quality for the deployed platform agent | `deploy_managed_agent.py` |

**Cost Optimization**: By routing simple classification to Haiku ($0.80/M input) instead of Opus ($15/M input), classification costs are reduced by **95%**.

### 3.2 Orchestrator Pattern

The `PharmaOrchestrator` implements a hierarchical routing architecture:

```
User Query: "What are the CYP interactions for Nexavirin?"
            |
            v
   +------------------+
   | Haiku Classifier  |   <-- Fast, cheap classification
   | Prompt: "Classify  |
   |  into one of 5     |
   |  domains..."       |
   +--------+----------+
            |
            v
   {"domain": "drug_discovery", "confidence": 0.92}
            |
            v  (confidence >= 0.7)
   +------------------+
   | Drug Discovery    |   <-- Specialized Opus agent
   | Agent (lazy-init) |       with domain prompt + tools
   +--------+----------+
            |
            v
   Tools: drug_lookup -> drug_interaction_check
            |
            v
   Final synthesized response with CYP analysis
```

**Classifier Prompt** (sent to Haiku 4.5):
```
Classify this query into one of: drug_discovery, clinical_trials,
regulatory, safety, general. Return JSON with domain, confidence (0-1),
and reasoning.
```

**Routing Rules**:
- `confidence >= 0.7` AND domain has agent config -> route to specialized sub-agent
- Otherwise -> use main orchestrator agent (has all tools)
- Classifier errors -> default to "general" (main agent)

### 3.3 Sub-Agent Configuration

Each sub-agent is configured with:

```python
AGENT_CONFIGS = {
    "drug_discovery": {
        "system_prompt": "You are a medicinal chemistry expert...",
        "tools": [DrugLookupTool, DrugInteractionTool],
        "use_thinking": True,   # Extended thinking ON
        "model": "claude-opus-4-6"
    },
    "clinical_trials": {
        "system_prompt": "You are a clinical research specialist...",
        "tools": [TrialSearchTool, AdverseEventSearchTool, SafetySignalTool],
        "use_thinking": True,
        "model": "claude-opus-4-6"
    },
    "regulatory": {
        "system_prompt": "You are an FDA regulatory affairs expert...",
        "tools": [DocumentGeneratorTool, TrialSearchTool, ...],
        "use_thinking": False,  # Thinking OFF (straightforward generation)
        "model": "claude-opus-4-6"
    },
    "safety": {
        "system_prompt": "You are a pharmacovigilance expert...",
        "tools": [SafetySignalTool, AdverseEventSearchTool],
        "use_thinking": True,
        "model": "claude-opus-4-6"
    }
}
```

**Lazy Loading**: Sub-agents are only instantiated when their domain is first requested, reducing memory footprint.

### 3.4 Extended Thinking Configuration

Extended thinking is selectively enabled for domains requiring complex reasoning:

```python
# In base_agent.py, during LLM request construction:
if use_thinking:
    request_params["thinking"] = {
        "type": "enabled",
        "budget_tokens": 10000   # Configurable via THINKING_BUDGET_TOKENS
    }
```

| Domain | Thinking | Rationale |
|--------|----------|-----------|
| Drug Discovery | ON | SAR analysis, CYP metabolism chains, Lipinski reasoning |
| Clinical Trials | ON | Statistical interpretation, endpoint analysis |
| Safety | ON | Benefit-risk tradeoffs, signal causality reasoning |
| Regulatory | OFF | Structured document generation is formulaic |

### 3.5 Prompt Caching Strategy

The system uses Claude's prompt caching to dramatically reduce costs in multi-turn conversations:

```python
def _build_system_prompt(self) -> list[dict]:
    parts = []

    # CACHED: Core system prompt (stable, 1500+ tokens)
    parts.append({
        "type": "text",
        "text": self.system_prompt,
        "cache_control": {"type": "ephemeral"}  # 5-minute TTL
    })

    # NOT CACHED: Memory context (changes per request)
    memory_context = self.memory.get_context_for_agent(self.name)
    if memory_context:
        parts.append({
            "type": "text",
            "text": f"\n\n{memory_context}"
            # No cache_control -- fresh each time
        })

    return parts
```

**How It Works**:
- First request: System prompt written to cache (cost: 18.75/M tokens for Opus)
- Subsequent requests within 5 minutes: Read from cache (cost: 1.50/M tokens)
- This is a **90% cost reduction** on the system prompt portion
- Memory context is injected *after* the cached block so it stays fresh

**Cache Hit Rate Tracking**:
```python
cache_hit_rate = cache_read_tokens / (input_tokens + cache_read_tokens)
# Target: >50% for multi-turn conversations
```

### 3.6 Skill Files (Domain Expertise Injection)

Each domain has a `SKILL.md` file in `.claude/skills/` that provides deep domain expertise:

| Skill File | Topics Covered |
|-----------|---------------|
| `drug-discovery/SKILL.md` | SAR analysis, ADMET assessment, toxicophore flagging, Lipinski Rule of Five, lead optimization |
| `clinical-trials/SKILL.md` | Trial design patterns, biostatistics, DSMB briefings, adaptive trials, interim analysis |
| `regulatory-docs/SKILL.md` | Document structure per FDA/ICH, regulatory pathways (510k, PMA, IND), submission timelines |
| `safety-monitoring/SKILL.md` | Signal detection algorithms, causality (WHO-UMC), Bradford Hill criteria, benefit-risk frameworks |

These are loaded contextually when the Claude Code agent operates in the respective domain.

---

## 4. Tool System Design

### 4.1 Tool Definitions

All 6 tools follow a consistent pattern:

```python
class DrugLookupTool:
    NAME = "drug_lookup"
    DESCRIPTION = "Search the pharmaceutical compound library..."
    INPUT_SCHEMA = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "..."},
            "field": {"type": "string", "enum": [...]}
        },
        "required": ["query"]
    }

    @staticmethod
    def execute(query: str, field: str = "any") -> str:
        # Load data, search, return JSON string
        ...
```

### 4.2 Tool Inventory

| Tool | Input | Output | Data Source |
|------|-------|--------|-------------|
| `drug_lookup` | query, field | Compound profiles + Lipinski assessment | `drugs_compound_library.json` |
| `drug_interaction_check` | compound_names[] | CYP interaction pairs with risk levels | `drugs_compound_library.json` |
| `trial_search` | query, field | Trial details + enrollment progress | `clinical_trials.json` |
| `adverse_event_search` | compound, trial_id, serious_only, min_grade | AE records + summary stats | `adverse_events.json` |
| `safety_signal_analysis` | compound_name | Signal detection with SOC disproportionality | `adverse_events.json` + `clinical_trials.json` |
| `generate_document` | document_type, compound_name, fields | Regulatory scaffold with compliance metadata | `regulatory_templates.json` |

### 4.3 Tool Loop (Agentic Execution)

The base agent implements an agentic tool loop that allows Claude to call tools iteratively:

```
Iteration 1:
  User: "Analyze Nexavirin safety and generate a report"
  Claude thinks -> calls drug_lookup(query="Nexavirin")
  Tool returns compound data

Iteration 2:
  Claude processes results -> calls safety_signal_analysis(compound_name="Nexavirin")
  Tool returns signal data

Iteration 3:
  Claude processes results -> calls adverse_event_search(compound_name="Nexavirin")
  Tool returns AE data

Iteration 4:
  Claude synthesizes all data -> generates final text response
  stop_reason: "end_turn" -> loop exits
```

**Loop Configuration**:
- Maximum iterations: **10** (prevents runaway loops)
- Exit condition: `stop_reason != "tool_use"` OR no `tool_use` blocks in response
- Each iteration: full conversation history sent (including prior tool results)

### 4.4 Tool Registration for Managed Agent

When deploying to platform.claude.com, tools are registered as `"type": "custom"` with JSON Schema:

```python
# In deploy_managed_agent.py
CUSTOM_TOOLS = [
    {
        "type": "custom",
        "name": "drug_lookup",
        "description": "Search the pharmaceutical compound library...",
        "input_schema": { ... }
    },
    # ... 5 more tools
]

agent = client.beta.agents.create(
    name="PharmaAgent Pro",
    model="claude-sonnet-4-6",
    system=SYSTEM_PROMPT,
    tools=[
        {"type": "agent_toolset_20260401", "configs": [...]},  # Built-in tools
        *CUSTOM_TOOLS,                                          # Custom tools
    ],
)
```

**Custom Tool Execution Flow** (Managed Agent):
1. Agent emits `agent.custom_tool_use` event with `name`, `input`, `id`
2. Client executes tool locally (tool results never leave the client)
3. Session goes idle with `stop_reason.type == "requires_action"`
4. Client sends `user.custom_tool_result` with `custom_tool_use_id` matching the event `id`
5. Agent resumes processing with tool result

---

## 5. LLM Strategy & Data Retrieval

### 5.1 How Data Retrieval Works (No RAG)

PharmaAgent Pro does **not** use a traditional RAG (Retrieval-Augmented Generation) pipeline with vector embeddings. Instead, it uses a **tool-based retrieval** approach:

```
+-----------+     +----------+     +----------+     +-----------+
| User      | --> | Claude   | --> | Tool     | --> | JSON      |
| Query     |     | decides  |     | executes |     | Dataset   |
|           |     | which    |     | search   |     | (local)   |
|           |     | tool to  |     | logic    |     |           |
|           |     | call     |     |          |     |           |
+-----------+     +----------+     +----------+     +-----------+
                       ^                |
                       |                |
                       +--- results ----+
                       Claude synthesizes
                       the final answer
```

**Why Tool-Based Retrieval Instead of RAG?**

| Factor | Tool-Based (Our Approach) | RAG with Embeddings |
|--------|--------------------------|---------------------|
| **Data size** | 4 focused JSON files (~50KB total) | Better for millions of documents |
| **Precision** | Exact field matching (compound_id, trial_id) | Semantic similarity (may miss exact matches) |
| **Transparency** | Claude explicitly names the tool it calls | Retrieval is opaque to the user |
| **Structured data** | Native JSON filtering, aggregation | Requires flattening for embedding |
| **Compliance** | Tool calls fully auditable | Embedding retrieval harder to audit |
| **Cost** | No embedding model costs | Requires embedding API calls |

**When RAG Would Be Appropriate**: If the dataset grows to thousands of documents (e.g., full FDA label database, literature corpus), a vector store with semantic search would be added as an additional tool.

### 5.2 Memory Store (Local Persistent Context)

The memory store (`src/memory/memory_store.py`) provides persistent context across sessions:

```
store_root/
  index.json                # Master index of all memories
  memories/
    <sha256_hash>.json      # Current state of each memory
  versions/
    <sha256_hash>/
      v1.json, v2.json ...  # Immutable version history
```

**Operations**:
- `write(path, content, tags)` -- Create/update with auto-versioning
- `search(query, tags, limit)` -- Full-text + tag-based search
- `get_context_for_agent(agent_name)` -- Inject relevant memories into system prompt
- `list_memories(prefix)` -- Browse by path hierarchy

**How Memory Enhances Responses**:
1. Before each LLM call, `get_context_for_agent()` searches for memories tagged with the active agent
2. Matching memories are formatted as markdown and injected after the (cached) system prompt
3. This allows the agent to "remember" prior drug analyses, user preferences, and safety flags
4. Memory is injected *outside* the cache boundary so it stays fresh

**Note**: This is a local file-based store. The Managed Agent platform's `memory_stores` API is in research preview and is gracefully degraded (set to `null`) if unavailable.

### 5.3 Prompt Caching (Not a Traditional Cache)

Prompt caching is a Claude API feature, not a local cache layer. It works at the API level:

```
Request 1 (cache MISS):
  system_prompt (1500 tokens) -> WRITE to cache   -> cost: $18.75/M
  memory_context (200 tokens) -> normal input      -> cost: $15.00/M
  messages (500 tokens)       -> normal input      -> cost: $15.00/M

Request 2 within 5 minutes (cache HIT):
  system_prompt (1500 tokens) -> READ from cache   -> cost: $1.50/M  (90% savings)
  memory_context (200 tokens) -> normal input      -> cost: $15.00/M
  messages (800 tokens)       -> normal input      -> cost: $15.00/M
```

The usage tracker records `cache_creation_tokens` and `cache_read_tokens` separately for cost analysis.

---

## 6. Environment & Session Management

### 6.1 Managed Agent Environment

The deployment creates a cloud environment on platform.claude.com:

```python
environment = client.beta.environments.create(
    name="pharma-agent-env",
    config={
        "type": "cloud",
        "packages": {
            "pip": ["pandas", "jinja2", "rich"],
        },
        "networking": {"type": "unrestricted"},
    },
)
```

This environment provides an isolated runtime where the managed agent can execute built-in tools (bash, file operations, web search).

### 6.2 Session Lifecycle

```
  Create Session
       |
       v
  session.status_idle (stop_reason: end_turn)
       |
       v  <-- User sends message
  session.status_running
       |
       +-- agent.thinking (extended reasoning)
       +-- agent.message (text blocks)
       +-- agent.tool_use (built-in tools)
       +-- agent.custom_tool_use (pharma tools)
       |        |
       |        v
       |   Client executes tool locally
       |        |
       |        v
       +-- session.status_idle (stop_reason: requires_action)
       |        |
       |        v
       |   Client sends user.custom_tool_result
       |        |
       |        v
       +-- session.status_running (resumes)
       |
       v
  session.status_idle (stop_reason: end_turn)
       |
       v
  Ready for next message
```

### 6.3 Local Session Management

The local API server (`src/api.py`) maintains per-session orchestrator instances:

```python
_sessions: dict[str, PharmaOrchestrator] = {}

# Each session gets its own:
# - Conversation history (full message list)
# - Sub-agent instances (lazy-loaded)
# - Memory context
# - Usage tracking
```

---

## 7. Multi-Turn Conversation & Reuse

### 7.1 Conversation Context Retention

Multi-turn conversation is fully enabled:

```python
# In base_agent.py
class BaseAgent:
    def __init__(self):
        self.messages: list[dict] = []   # Full conversation history

    def chat(self, user_message: str):
        self.messages.append({"role": "user", "content": sanitized_input})

        response = client.messages.create(
            messages=self.messages,  # ALL prior turns included
            ...
        )

        self.messages.append({"role": "assistant", "content": response.content})
```

**Example Multi-Turn Flow**:
```
Turn 1: "Tell me about Nexavirin"
  -> Agent calls drug_lookup, returns compound profile
  -> Messages: [user_1, assistant_1(with tool results)]

Turn 2: "What are its CYP interactions?"
  -> "its" correctly resolves to Nexavirin from context
  -> Agent calls drug_interaction_check
  -> Messages: [user_1, assistant_1, user_2, assistant_2]

Turn 3: "Compare that with Oncolytin-B"
  -> "that" resolves to CYP interaction profile
  -> Agent has full context from prior turns
```

### 7.2 How Similar Questions Benefit from Prior Context

When a user asks follow-up or similar questions, the system benefits in three ways:

1. **Conversation History**: Prior tool results are already in the message history. Claude can reference them without re-calling tools.

2. **Prompt Cache Hits**: The system prompt is cached for 5 minutes. Follow-up questions within the same session reuse the cached prompt, reducing costs by ~90% on that portion.

3. **Memory Store**: If the agent saves key findings to the memory store during a session, subsequent sessions can retrieve that context automatically.

**Example Reuse**:
```
Session 1, Turn 1: "Analyze Nexavirin safety"
  -> Calls 3 tools, generates analysis
  -> Agent saves key findings to memory: /drugs/nexavirin/safety_summary

Session 2, Turn 1: "What safety concerns exist for Nexavirin?"
  -> Memory context injected: prior safety summary
  -> Agent still calls tools for latest data
  -> But synthesizes faster with prior context
```

### 7.3 Session Reset

Users can reset conversation history without losing memory:

```bash
# CLI
/reset

# API
POST /reset {"session_id": "abc123"}
```

This clears `self.messages` but preserves the memory store and audit trail.

---

## 8. Guardrails & Compliance

### 8.1 Guardrail Pipeline

Every request passes through a four-stage guardrail pipeline:

```
Input
  |
  v
[1] Rate Limiter        -- Per-user sliding window (30 req/min)
  |                        Blocks: "Rate limit exceeded. Reset in Xs."
  v
[2] Input Validator     -- PII detection + redaction
  |                        Prompt injection detection (7 patterns)
  |                        Prohibited topic blocking (3 categories)
  v
[3] LLM Processing      -- Claude generates response with tools
  |
  v
[4] Output Filter       -- PII redaction at output boundary
  |                        Medical advice warnings
  |                        Absolute claim detection
  |                        Compliance footer injection
  v
Output
```

### 8.2 PII Handling

**Detection Patterns** (input + output):
| PII Type | Pattern | Replacement |
|----------|---------|-------------|
| SSN | `\d{3}-\d{2}-\d{4}` | `[REDACTED_SSN]` |
| Email | Standard email regex | `[REDACTED_EMAIL]` |
| Phone | `\d{3}-\d{3}-\d{4}` | `[REDACTED_PHONE]` |
| Medical Record # | `MRN[-:]?\s*\d+` | `[REDACTED_MRN]` |
| Date of Birth | `DOB[-:]?\s*\d{1,2}/\d{1,2}/\d{2,4}` | `[REDACTED_DOB]` |
| Credit Card | `\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}` | `[REDACTED_CC]` |

**Guarantee**: PII is redacted *before* being sent to the Claude API and again *after* response generation.

### 8.3 Compliance Validation

The compliance checker validates regulatory documents against standards:

| Document Type | Standard | Validates |
|--------------|----------|-----------|
| IND Annual Report | 21 CFR 312.33 | ind_number, sponsor, 8 required sections |
| Clinical Study Report | ICH E3 | study_id, phase, 10 required sections |
| CIOMS Safety Report | ICH E2A | ae_id, event_term, 4 required sections |
| DSUR | ICH E2F | development_phase, DIBD, 8 required sections |
| Investigator's Brochure | ICH E6(R2) | version, date, 5 required sections |

---

## 9. Development Process

### 9.1 Setup

```bash
# Clone and install
git clone <repo-url> && cd ClaudeManagedAgentApp
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Configure
cp .env.example .env
# Set ANTHROPIC_API_KEY in .env
```

### 9.2 Testing

```bash
# Run all 71+ tests (no API key needed for unit tests)
pytest tests/ -v

# Test coverage
pytest tests/ --cov=src --cov-report=html

# Individual test suites
pytest tests/test_tools.py -v        # 30+ tool tests
pytest tests/test_guardrails.py -v   # 20+ guardrail tests
pytest tests/test_memory.py -v       # 10+ memory tests
pytest tests/test_utils.py -v        # 15+ utility tests
```

### 9.3 Local Development Modes

| Mode | Command | Description |
|------|---------|-------------|
| Interactive CLI | `python -m src.main` | Multi-turn chat with slash commands |
| API Server | `python -m src.main --mode api` | FastAPI on port 8000 with `/docs` |
| Managed Agent Chatbot (Terminal) | `python deploy/chatbot.py` | Connects to platform.claude.com |
| Managed Agent Chatbot (Web) | `python deploy/chatbot_server.py` | Web UI on port 3000 |

---

## 10. Deployment Process

### 10.1 Deployment Sequence

The deployment to platform.claude.com follows a 4-step process:

```
Step 1: Create Agent
  |  POST /v1/agents
  |  - Name, model (Sonnet 4.6), system prompt
  |  - Built-in toolset (bash, read, write, edit, glob, grep, web_search, web_fetch)
  |  - 6 custom tools with JSON Schema definitions
  |  -> Returns: agent_id, version
  v
Step 2: Create Environment
  |  POST /v1/environments
  |  - Type: cloud
  |  - Packages: pandas, jinja2, rich
  |  - Networking: unrestricted
  |  -> Returns: environment_id
  v
Step 3: Create Memory Store (optional)
  |  POST /v1/memory_stores
  |  - Seed with pharma context (/pharma/*, /data/*)
  |  - Currently: research preview, gracefully degraded
  |  -> Returns: memory_store_id or null
  v
Step 4: Create Session
  |  POST /v1/sessions
  |  - Links: agent_id + environment_id
  |  - Optionally attaches memory_store
  |  -> Returns: session_id
  v
State Persisted to deploy_state.json:
  {
    "agent_id": "agent_...",
    "environment_id": "env_...",
    "memory_store_id": null,
    "session_id": "sesn_..."
  }
```

### 10.2 Running the Deployment

```bash
# Set API key
export ANTHROPIC_API_KEY=sk-ant-...

# Deploy (idempotent -- skips existing resources)
python deploy/deploy_managed_agent.py

# Launch chatbot
python deploy/chatbot.py           # Terminal
python deploy/chatbot_server.py    # Web UI at http://localhost:3000
```

### 10.3 Deployment Architecture (Managed Agent)

```
  +---------------------+          +---------------------------+
  |  Local Client        |          |  platform.claude.com       |
  |                      |          |                            |
  |  chatbot.py /        |  SSE     |  +--------------------+   |
  |  chatbot_server.py   | <------> |  | Managed Agent      |   |
  |                      | stream   |  | (Sonnet 4.6)       |   |
  |  +----------------+  |          |  | + system prompt     |   |
  |  | Tool Executors  | |          |  | + built-in tools    |   |
  |  | (drug_lookup,   | |          |  | + custom tool defs  |   |
  |  |  trial_search,  | |          |  +--------+-----------+   |
  |  |  etc.)          | |          |           |               |
  |  +--------+-------+ |          |  +--------v-----------+   |
  |           |          |          |  | Cloud Environment   |   |
  |  Local JSON datasets |          |  | (pandas, jinja2)    |   |
  |  (src/datasets/)     |          |  +--------------------+   |
  +---------------------+          +---------------------------+
```

**Key Point**: Custom tools execute **locally** on the client. The managed agent sends tool call requests; the client executes them against local datasets and returns results. No pharma data is uploaded to the platform.

---

## 11. Process Flow Diagrams

### 11.1 End-to-End Request Flow

```
User types: "Run safety signal analysis on Oncolytin-B"
  |
  v
[Rate Limiter] Check: user "default", 30 req/min
  | PASS (23 remaining)
  v
[Input Validator]
  | PII check: none detected
  | Injection check: clean
  | Prohibited topics: clean
  | Sanitized input: unchanged
  v
[Orchestrator] -> [Haiku Classifier]
  | Classification: {"domain": "safety", "confidence": 0.95}
  | Route: Safety Agent (Opus 4.6 + Thinking)
  v
[Safety Agent] -> [Claude Opus 4.6 API Call #1]
  | System prompt: cached (cache HIT, 1.5/M tokens)
  | Memory context: 1 prior safety memory injected
  | Messages: [user message]
  | Thinking: enabled (10K budget)
  |
  | Claude thinks: "I need to analyze Oncolytin-B safety..."
  | Claude calls: safety_signal_analysis(compound_name="Oncolytin-B")
  v
[Tool Executor] safety_signal_analysis
  | Loads adverse_events.json + clinical_trials.json
  | Filters for Oncolytin-B
  | Calculates: 3 events, 2 SAEs, 2 Grade 3+
  | Signal: ALERT (ILD in Respiratory SOC, >30%)
  | Returns JSON with signal status
  v
[Safety Agent] -> [Claude Opus 4.6 API Call #2]
  | Messages: [user, assistant(tool_call), user(tool_result)]
  | Claude calls: adverse_event_search(compound_name="Oncolytin-B", serious_only=true)
  v
[Tool Executor] adverse_event_search
  | Returns 2 SAE records with full narratives
  v
[Safety Agent] -> [Claude Opus 4.6 API Call #3]
  | Claude synthesizes all data into final response
  | stop_reason: "end_turn"
  v
[Output Filter]
  | PII redaction: 0 redactions
  | Medical advice check: 0 warnings
  | Compliance footer: "Safety assessment auto-generated..."
  v
[Audit Logger]
  | Logs: query event, 2 tool_use events, response event
  v
[Usage Tracker]
  | Records: 3 API calls, ~5000 input tokens, ~2000 output tokens
  | Cache: 1500 tokens read from cache
  | Estimated cost: $0.19
  v
Response displayed to user with thinking preview
```

### 11.2 Managed Agent Custom Tool Flow

```
                 Client                          Platform
                   |                                |
  user message --> |  -- user.message event ------> |
                   |                                | Agent processes
                   |  <-- agent.thinking ---------- |
                   |  <-- agent.custom_tool_use ---- | (drug_lookup)
                   |        id: "evt_abc123"         |
                   |        input: {query: "EGFR"}   |
                   |                                |
  Execute tool     |                                | Session goes idle
  locally          |  <-- session.status_idle ------ | stop_reason:
  drug_lookup()    |       requires_action           |   requires_action
                   |       event_ids: ["evt_abc123"] |
                   |                                |
  Send result ---> | -- user.custom_tool_result --> |
                   |    custom_tool_use_id:          |
                   |      "evt_abc123"               |
                   |    content: [{text: "..."}]     |
                   |                                | Agent resumes
                   |  <-- agent.message ----------- | Final response
                   |  <-- session.status_idle ------ | stop_reason:
                   |       end_turn                  |   end_turn
```

---

## 12. FAQ & Troubleshooting

### Frequently Asked Questions

**Q: Does PharmaAgent Pro use RAG?**
A: No. It uses tool-based retrieval where Claude decides which tool to call, and tools execute deterministic searches against structured JSON datasets. This provides exact matching, full auditability, and zero embedding costs. See Section 5.1.

**Q: Is patient data sent to Claude?**
A: No. PII is detected and redacted at the input boundary before any API call. Output is also filtered. The audit trail logs all redactions.

**Q: How does multi-turn context work?**
A: Full conversation history is maintained in `self.messages` and sent with every API call. Claude naturally resolves references like "its", "that compound", etc. from prior turns.

**Q: Why Sonnet for the managed agent instead of Opus?**
A: The managed agent on platform.claude.com handles general orchestration. Complex domain reasoning happens in the local sub-agents (Opus). Sonnet provides balanced quality/cost for the platform layer.

**Q: How are costs controlled?**
A: Three mechanisms: (1) Haiku for classification (95% cheaper than Opus), (2) prompt caching (90% savings on repeated prompts), (3) rate limiting (30 req/min per user).

**Q: What happens if the memory store API isn't available?**
A: The system gracefully degrades. `memory_store_id` is set to `null`, and the local memory store (`src/memory/`) is used instead. No functionality is lost.

### Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `ANTHROPIC_API_KEY not set` | Missing .env or env var | Set key in `.env` file |
| `events.0.tool_use_id: Extra inputs are not permitted` | Wrong field name in custom tool result | Use `custom_tool_use_id` (not `tool_use_id`) |
| `Rate limit exceeded` | Too many requests | Wait for reset or increase `RATE_LIMIT_PER_MINUTE` |
| `Session terminated` | Session expired or errored | Create new session via `POST /api/new-session` |
| `Memory Store API not available` | Research preview API | Expected behavior -- uses local memory fallback |

---

## 13. Roadmap

### Phase 1: Foundation Hardening (Current + Next 2 Months)

- [ ] **Vector Search Integration** -- Add embedding-based retrieval for large document corpora (FDA labels, literature)
- [ ] **Streaming Responses** -- Stream LLM output token-by-token in CLI and Web UI for perceived latency reduction
- [ ] **Session Persistence** -- Persist conversation history to disk for cross-restart session recovery
- [ ] **Managed Agent Memory Store** -- Adopt platform memory_stores API when it exits research preview
- [ ] **Comprehensive Error Recovery** -- Retry logic for transient API errors with exponential backoff

### Phase 2: Multi-Agent Orchestration (Months 3-5)

- [ ] **Parallel Agent Execution** -- Run drug_discovery + safety agents concurrently for cross-domain queries
- [ ] **Agent-to-Agent Communication** -- Allow the safety agent to request data from the clinical trials agent
- [ ] **Supervisor Agent** -- Meta-agent that reviews sub-agent outputs for consistency and completeness
- [ ] **Dynamic Tool Discovery** -- Agents can request tools from other agents at runtime
- [ ] **Conflict Resolution** -- When two agents disagree (e.g., risk vs. benefit), escalate to supervisor

### Phase 3: Enterprise Features (Months 6-9)

- [ ] **Role-Based Access Control (RBAC)** -- Different tool permissions for researchers, clinicians, regulatory staff
- [ ] **Real-Time Data Connectors** -- FDA FAERS API, ClinicalTrials.gov API, PubMed integration
- [ ] **Document Versioning & Approval Workflows** -- Track regulatory document revisions with approval chains
- [ ] **Multi-Tenant Support** -- Isolated memory, audit, and sessions per organization
- [ ] **Scheduled Monitoring** -- Automated daily safety signal scans with alert notifications

### Phase 4: Advanced Intelligence (Months 9-12)

- [ ] **Literature-Augmented Analysis** -- RAG over biomedical literature for evidence-based recommendations
- [ ] **Predictive Safety Modeling** -- Use historical AE data to predict safety signals for new compounds
- [ ] **Automated Regulatory Submission Prep** -- End-to-end IND/NDA package assembly with compliance pre-check
- [ ] **Multi-Modal Analysis** -- Ingest molecular structure images, clinical study charts, lab reports
- [ ] **Federated Learning** -- Cross-organization safety signal sharing without exposing raw data

### Deployment Roadmap

| Milestone | Target | Description |
|-----------|--------|-------------|
| MVP (current) | Done | Local + managed agent deployment, 6 tools, 4 agents |
| CI/CD Pipeline | Month 1 | Automated testing + deployment via GitHub Actions |
| Staging Environment | Month 2 | Pre-production validation with synthetic data |
| Production Deployment | Month 3 | Docker/Kubernetes with monitoring, alerting, autoscaling |
| SOC 2 Compliance | Month 6 | Audit trail hardening, encryption at rest, access logging |
| GxP Validation | Month 9 | 21 CFR Part 11 compliance for regulated use |
