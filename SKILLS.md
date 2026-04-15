# PharmaAgent Pro — Skills Catalog

This document describes the **domain skills** exposed by PharmaAgent Pro. Each skill is a specialized sub-agent defined in [src/agents/orchestrator.py](src/agents/orchestrator.py) (`AGENT_CONFIGS`) and backed by a subset of the custom tools in [src/tools/](src/tools/). Queries are routed to a skill by the Haiku 4.5 classifier; low-confidence or multi-domain queries fall through to the orchestrator, which has access to every tool.

---

## Routing

| Domain key | Trigger keywords (classifier) | Model | Extended thinking |
|------------|-------------------------------|-------|--------------------|
| `drug_discovery` | compound analysis, molecular properties, drug-likeness, interactions, SAR | Opus 4.6 | ✅ |
| `clinical_trials` | trial design, enrollment, endpoints, efficacy data, trial search | Opus 4.6 | ✅ |
| `regulatory` | document generation, FDA compliance, ICH, submissions | Sonnet 4.6 | ❌ |
| `safety` | adverse events, signal detection, benefit-risk, pharmacovigilance | Opus 4.6 | ✅ |
| `general` | greetings, help, multi-domain, unclear | Orchestrator (Opus 4.6) | configurable |

Routing uses a confidence threshold of **0.7** — below that, the orchestrator handles the query directly with the full toolset.

---

## Skill: Drug Discovery

**Role**: Medicinal-chemistry and computational-drug-design specialist.

**Tools**:
- `drug_lookup` — retrieve compound records from [src/datasets/drugs_compound_library.json](src/datasets/drugs_compound_library.json)
- `drug_interaction_check` — compare multiple compounds for DDIs and CYP liabilities

**Required behaviors**:
- Always call `drug_lookup` before analyzing any compound.
- Include **Lipinski Rule of Five** assessment in every compound review.
- Flag **CYP interaction liabilities** prominently.
- Never fabricate data — only use tool outputs.
- Use extended thinking for non-trivial SAR or optimization reasoning.

**Example prompts**:
- "Look up compound Nexavirin and assess its drug-likeness."
- "Check for drug interactions between Inflammablock and Oncolytin-B."

---

## Skill: Clinical Trials Research

**Role**: Trial-design, biostatistics, and operations specialist.

**Tools**:
- `trial_search` — query [src/datasets/clinical_trials.json](src/datasets/clinical_trials.json)
- `adverse_event_search` — query trial AE records
- `safety_signal_analysis` — statistical signal detection

**Required behaviors**:
- Retrieve trial data via `trial_search` before analysis.
- Include **enrollment progress percentages** in trial summaries.
- Report efficacy with **hazard ratios and 95% CIs** where available.
- Highlight SAEs and safety signals.
- Never extrapolate beyond the returned data.

**Example prompts**:
- "Show me the status of the ONCOLYZE-3 Phase III trial."
- "What are the enrollment rates across all active trials?"

---

## Skill: Regulatory Affairs

**Role**: FDA / ICH / global submission specialist. Generates compliant document scaffolds.

**Tools**:
- `generate_document` — render regulatory templates from [src/datasets/regulatory_templates.json](src/datasets/regulatory_templates.json)
- `trial_search`, `adverse_event_search`, `drug_lookup` — source data for documents

**Required behaviors**:
- Cite specific regulatory standards (e.g., **21 CFR 312.33**, ICH E2B(R3)).
- Include compliance checklists and confidentiality notices in generated docs.
- Flag data gaps that would block submission.
- Use formal regulatory language appropriate for FDA / EMA review.
- Every document is marked **"requires human review before submission."**

**Example prompts**:
- "Generate a CIOMS safety report for the Immunex-340 hepatitis SAE."
- "Draft an IND annual report cover for Study ONCOLYZE-3."

---

## Skill: Safety & Pharmacovigilance

**Role**: Signal detection, benefit-risk, and expedited-reporting specialist.

**Tools**:
- `safety_signal_analysis` — disproportionality / signal metrics
- `adverse_event_search`, `trial_search`, `drug_lookup`

**Required behaviors**:
- **Lead with the most serious findings** — never bury SAEs.
- Grade adverse events using **CTCAE v5.0**.
- Include **causality assessment** (WHO-UMC or equivalent) for every AE discussed.
- Flag any SAE requiring **expedited reporting** (15-day / 7-day IND safety reports).
- Use extended thinking for benefit-risk analyses.
- Never downplay or minimize a signal.

**Example prompts**:
- "Run a safety signal analysis on Oncolytin-B."
- "Assess benefit-risk for continuing enrollment in ONCOLYZE-3 given the Grade 4 hepatic events."

---

## Orchestrator (General / Multi-Domain)

When the classifier returns `general` or confidence < 0.7, the orchestrator ([src/agents/orchestrator.py](src/agents/orchestrator.py)) handles the conversation directly with **all six tools** available. It is also responsible for:

- Maintaining multi-turn conversation state
- Applying input/output guardrails ([src/guardrails/](src/guardrails/))
- Writing to the memory store ([src/memory/memory_store.py](src/memory/memory_store.py))
- Emitting audit + usage records ([src/utils/audit.py](src/utils/audit.py), [src/utils/usage_tracker.py](src/utils/usage_tracker.py))

---

## Custom Tool Reference

| Tool | Purpose | Backing dataset |
|------|---------|-----------------|
| `drug_lookup` | Compound lookup by name / ID | `drugs_compound_library.json` |
| `drug_interaction_check` | DDI / CYP / contraindication check | `drugs_compound_library.json` |
| `trial_search` | Trial metadata & enrollment | `clinical_trials.json` |
| `adverse_event_search` | AE records filtered by drug / trial / severity | `adverse_events.json` |
| `safety_signal_analysis` | Signal detection statistics | `adverse_events.json` |
| `generate_document` | Render regulatory document scaffolds | `regulatory_templates.json` |

Tool implementations live in [src/tools/drug_tools.py](src/tools/drug_tools.py), [src/tools/trial_tools.py](src/tools/trial_tools.py), and [src/tools/document_tools.py](src/tools/document_tools.py). The Managed Agent deployment wires the same tools through the SSE custom-tool protocol — see [deploy/README.md](deploy/README.md).

---

## Guardrails Applied to Every Skill

- **Input validation** — schema and length checks ([src/guardrails/input_validator.py](src/guardrails/input_validator.py))
- **PII redaction** — patient identifiers stripped before any LLM call
- **Output filtering** — forbidden content, fabricated citations ([src/guardrails/output_filter.py](src/guardrails/output_filter.py))
- **Compliance checks** — regulatory metadata headers, human-review disclaimers ([src/guardrails/compliance.py](src/guardrails/compliance.py))
- **Rate limiting** — per-user quotas ([src/guardrails/rate_limiter.py](src/guardrails/rate_limiter.py))

---

## Adding a New Skill

1. Add a new entry to `AGENT_CONFIGS` in [src/agents/orchestrator.py](src/agents/orchestrator.py) with `name`, `system_prompt`, `tools`, and `use_thinking`.
2. If it needs new tools, implement them under [src/tools/](src/tools/) and register them in `ALL_TOOLS`.
3. Extend the classifier prompt (`classify_query`) with the new domain and keywords.
4. Add tests under `tests/` and document the skill in this file.
