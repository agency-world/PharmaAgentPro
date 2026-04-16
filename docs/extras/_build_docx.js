const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, LevelFormat, PageBreak,
  HeadingLevel, BorderStyle, WidthType, ShadingType, PageNumber,
  SectionType, TabStopType, TabStopPosition,
} = require("docx");

// ── Colors ──
const NAVY = "1A365D";
const BLUE = "3B82F6";
const GRAY = "64748B";
const LIGHT_GRAY = "94A3B8";
const CODE_BG = "F1F5F9";
const HEADER_FILL = NAVY;
const ALT_ROW = "F8FAFC";
const WHITE = "FFFFFF";

// ── Borders ──
const border = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
const borders = { top: border, bottom: border, left: border, right: border };
const noBorder = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
const noBorders = { top: noBorder, bottom: noBorder, left: noBorder, right: noBorder };

// ── Page dimensions (US Letter, 1-inch margins) ──
const PAGE_W = 12240;
const PAGE_H = 15840;
const MARGIN = 1440;
const CONTENT_W = PAGE_W - 2 * MARGIN; // 9360

// ── Cell margins constant ──
const CELL_MARGINS = { top: 80, bottom: 80, left: 120, right: 120 };

// ── Helpers ──
function blankPara(count) {
  const out = [];
  for (let i = 0; i < count; i++) out.push(new Paragraph({ children: [] }));
  return out;
}

function textRun(text, opts = {}) {
  return new TextRun({
    text,
    font: opts.font || "Arial",
    size: opts.size || 24,
    bold: opts.bold || false,
    italics: opts.italics || false,
    color: opts.color || "000000",
  });
}

function codeParagraph(line) {
  return new Paragraph({
    spacing: { before: 0, after: 0, line: 260 },
    shading: { fill: CODE_BG, type: ShadingType.CLEAR },
    children: [
      new TextRun({
        text: line,
        font: "Courier New",
        size: 18, // 9pt
        color: "1E293B",
      }),
    ],
  });
}

function codeBlock(text) {
  const lines = text.split("\n");
  return lines.map((l, i) =>
    new Paragraph({
      spacing: { before: i === 0 ? 120 : 0, after: i === lines.length - 1 ? 120 : 0, line: 260 },
      shading: { fill: CODE_BG, type: ShadingType.CLEAR },
      children: [
        new TextRun({
          text: l || " ",
          font: "Courier New",
          size: 18,
          color: "1E293B",
        }),
      ],
    })
  );
}

function bodyPara(text, opts = {}) {
  const children = [];
  // Parse bold segments: **text**
  const regex = /\*\*(.*?)\*\*/g;
  let lastIndex = 0;
  let match;
  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      children.push(textRun(text.slice(lastIndex, match.index), opts));
    }
    children.push(textRun(match[1], { ...opts, bold: true }));
    lastIndex = regex.lastIndex;
  }
  if (lastIndex < text.length) {
    children.push(textRun(text.slice(lastIndex), opts));
  }
  return new Paragraph({
    spacing: { before: 120, after: 120 },
    children,
  });
}

function heading1(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    children: [textRun(text, { size: 32, bold: true, color: NAVY })],
  });
}

function heading2(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    children: [textRun(text, { size: 28, bold: true, color: NAVY })],
  });
}

function heading3(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_3,
    children: [textRun(text, { size: 24, bold: true, color: NAVY })],
  });
}

// ── Table builder ──
function makeTable(headers, rows, colWidths) {
  const totalW = colWidths.reduce((a, b) => a + b, 0);

  function headerCell(text, w) {
    return new TableCell({
      borders,
      width: { size: w, type: WidthType.DXA },
      shading: { fill: HEADER_FILL, type: ShadingType.CLEAR },
      margins: CELL_MARGINS,
      children: [
        new Paragraph({
          children: [textRun(text, { size: 22, bold: true, color: WHITE })],
        }),
      ],
    });
  }

  function dataCell(text, w, rowIdx) {
    const fill = rowIdx % 2 === 0 ? ALT_ROW : WHITE;
    // Parse bold segments
    const children = [];
    const regex = /\*\*(.*?)\*\*/g;
    let lastIndex = 0;
    let match;
    while ((match = regex.exec(text)) !== null) {
      if (match.index > lastIndex) {
        children.push(textRun(text.slice(lastIndex, match.index), { size: 22 }));
      }
      children.push(textRun(match[1], { size: 22, bold: true }));
      lastIndex = regex.lastIndex;
    }
    if (lastIndex < text.length) {
      children.push(textRun(text.slice(lastIndex), { size: 22 }));
    }
    return new TableCell({
      borders,
      width: { size: w, type: WidthType.DXA },
      shading: { fill, type: ShadingType.CLEAR },
      margins: CELL_MARGINS,
      children: [new Paragraph({ children })],
    });
  }

  const tableRows = [];
  // Header row
  tableRows.push(
    new TableRow({
      children: headers.map((h, i) => headerCell(h, colWidths[i])),
    })
  );
  // Data rows
  rows.forEach((row, rIdx) => {
    tableRows.push(
      new TableRow({
        children: row.map((cell, i) => dataCell(cell, colWidths[i], rIdx)),
      })
    );
  });

  return new Table({
    width: { size: totalW, type: WidthType.DXA },
    columnWidths: colWidths,
    rows: tableRows,
  });
}

// ── Build the document ──
function buildDoc() {
  // Common header / footer
  const defaultHeader = new Header({
    children: [
      new Paragraph({
        tabStops: [{ type: TabStopType.RIGHT, position: TabStopPosition.MAX }],
        children: [
          textRun("PharmaAgent Pro -- Technical Guide", { size: 18, color: GRAY }),
          new TextRun({ children: ["\t"] }),
          textRun("Page ", { size: 18, color: GRAY }),
          new TextRun({ children: [PageNumber.CURRENT], font: "Arial", size: 18, color: GRAY }),
        ],
      }),
    ],
  });

  const defaultFooter = new Footer({
    children: [
      new Paragraph({
        alignment: AlignmentType.CENTER,
        children: [
          textRun("Confidential -- Internal Use Only", { size: 18, italics: true, color: GRAY }),
        ],
      }),
    ],
  });

  const pageProps = {
    page: {
      size: { width: PAGE_W, height: PAGE_H },
      margin: { top: MARGIN, right: MARGIN, bottom: MARGIN, left: MARGIN },
    },
  };

  // ────────────────────────────────────────────
  //  COVER PAGE (no header)
  // ────────────────────────────────────────────
  const coverSection = {
    properties: {
      ...pageProps,
      type: SectionType.NEXT_PAGE,
    },
    footers: {
      default: new Footer({
        children: [
          new Paragraph({
            alignment: AlignmentType.CENTER,
            children: [
              textRun("Confidential -- Internal Use Only", { size: 18, italics: true, color: GRAY }),
            ],
          }),
        ],
      }),
    },
    children: [
      ...blankPara(6),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        children: [textRun("PharmaAgent Pro", { size: 72, bold: true, color: NAVY })],
      }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { before: 200 },
        children: [textRun("Technical Guide", { size: 48, color: BLUE })],
      }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { before: 200 },
        children: [textRun("Product Design, Development & Deployment", { size: 28, color: GRAY })],
      }),
      ...blankPara(4),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        children: [textRun("Version 1.0 | April 2026 | Internal Technical Documentation", { size: 20, color: LIGHT_GRAY })],
      }),
      new Paragraph({ children: [new PageBreak()] }),
    ],
  };

  // ────────────────────────────────────────────
  //  TABLE OF CONTENTS
  // ────────────────────────────────────────────
  const tocItems = [
    "Product Overview",
    "System Architecture",
    "Agent Engineering & Configuration",
    "Tool System Design",
    "LLM Strategy & Data Retrieval",
    "Environment & Session Management",
    "Multi-Turn Conversation & Reuse",
    "Guardrails & Compliance",
    "Development Process",
    "Deployment Process",
    "Process Flow Diagrams",
    "FAQ & Troubleshooting",
    "Roadmap",
  ];

  const tocSection = {
    properties: {
      ...pageProps,
      type: SectionType.CONTINUOUS,
    },
    headers: { default: defaultHeader },
    footers: { default: defaultFooter },
    children: [
      heading1("Table of Contents"),
      ...tocItems.map(
        (item, i) =>
          new Paragraph({
            numbering: { reference: "numbers", level: 0 },
            children: [textRun(item, { size: 22, color: BLUE })],
          })
      ),
      new Paragraph({ children: [new PageBreak()] }),
    ],
  };

  // ────────────────────────────────────────────
  //  SECTION 1: Product Overview
  // ────────────────────────────────────────────
  const sec1 = {
    properties: { ...pageProps, type: SectionType.CONTINUOUS },
    headers: { default: defaultHeader },
    footers: { default: defaultFooter },
    children: [
      heading1("1. Product Overview"),
      heading2("What is PharmaAgent Pro?"),
      bodyPara("PharmaAgent Pro is a multi-agent pharmaceutical intelligence platform built on Claude's Managed Agent SDK. It serves pharmaceutical researchers, clinicians, and regulatory professionals with four core capabilities:"),
      makeTable(
        ["Domain", "Capability", "Key Functions"],
        [
          ["Drug Discovery", "Compound analysis", "Drug-likeness (Lipinski), ADMET profiling, CYP interactions, SAR analysis"],
          ["Clinical Trials", "Trial intelligence", "Trial status, enrollment tracking, endpoint analysis, interim results"],
          ["Regulatory Affairs", "Document generation", "IND reports, CSRs, CIOMS, DSURs, IBs -- FDA/ICH compliant"],
          ["Safety Monitoring", "Pharmacovigilance", "AE analysis, signal detection, benefit-risk assessment, SAE triage"],
        ],
        [2000, 2000, 5360]
      ),
      heading2("Design Principles"),
      new Paragraph({
        numbering: { reference: "numbers", level: 0 },
        children: [textRun("Safety First", { bold: true }), textRun(" -- PII redaction, prompt injection defense, compliance validation at every boundary")],
      }),
      new Paragraph({
        numbering: { reference: "numbers", level: 0 },
        children: [textRun("Transparent Reasoning", { bold: true }), textRun(" -- Extended thinking exposes Claude's reasoning chain for complex analyses")],
      }),
      new Paragraph({
        numbering: { reference: "numbers", level: 0 },
        children: [textRun("Cost Efficiency", { bold: true }), textRun(" -- Multi-model routing + prompt caching reduces LLM costs by 60-80%")],
      }),
      new Paragraph({
        numbering: { reference: "numbers", level: 0 },
        children: [textRun("Auditability", { bold: true }), textRun(" -- Every query, tool call, and response is logged in an immutable audit trail")],
      }),
      new Paragraph({
        numbering: { reference: "numbers", level: 0 },
        children: [textRun("Domain Fidelity", { bold: true }), textRun(" -- Pharma-specific tools, skill files, and guardrails ensure accurate, compliant outputs")],
      }),
      new Paragraph({ children: [new PageBreak()] }),
    ],
  };

  // ────────────────────────────────────────────
  //  SECTION 2: System Architecture
  // ────────────────────────────────────────────
  const sec2 = {
    properties: { ...pageProps, type: SectionType.CONTINUOUS },
    headers: { default: defaultHeader },
    footers: { default: defaultFooter },
    children: [
      heading1("2. System Architecture"),
      heading2("High-Level Architecture"),
      bodyPara("The system follows a layered architecture with clear separation of concerns:"),
      makeTable(
        ["Layer", "Components"],
        [
          ["User Interfaces", "CLI Chat, Web UI (port 3000), REST API (port 8000)"],
          ["Guardrails Layer", "Input Validator, Output Filter, Compliance Checker, Rate Limiter"],
          ["PharmaOrchestrator", "Query Classifier (Haiku 4.5) routes to 4 specialized sub-agents"],
          ["Sub-Agents", "Drug Discovery, Clinical Trials, Regulatory, Safety (all Opus 4.6)"],
          ["Tool Layer", "6 pharma-specific tools with JSON Schema definitions"],
          ["Infrastructure", "Prompt Cache (5-min TTL), Memory Store (versioned), Audit (JSONL), Usage Tracker"],
          ["Data Layer", "drugs_compound_library.json, clinical_trials.json, adverse_events.json, regulatory_templates.json"],
        ],
        [2500, 6860]
      ),
      heading2("Directory Structure"),
      ...codeBlock(
`ClaudeManagedAgentApp/
  src/
    main.py                 -- CLI + FastAPI entry point
    api.py                  -- REST API server (port 8000)
    agents/
      orchestrator.py       -- Query routing via Haiku classifier
      base_agent.py         -- Core LLM logic, tool loop, caching
    tools/
      drug_tools.py         -- DrugLookupTool, DrugInteractionTool
      trial_tools.py        -- TrialSearchTool, AdverseEventSearchTool, SafetySignalTool
      document_tools.py     -- DocumentGeneratorTool
    guardrails/             -- Input validation, output filtering, compliance, rate limiting
    memory/                 -- Versioned local file-based memory store
    utils/                  -- Config, logger, audit, usage tracker
    datasets/               -- 4 JSON pharma datasets
  .claude/
    skills/                 -- 4 domain SKILL.md files
    commands/               -- 4 slash command templates
  deploy/                   -- Managed agent deployment scripts + chatbot
  tests/                    -- 71+ tests across 4 files
  docs/                     -- Technical guide + marketing deck`
      ),
      new Paragraph({ children: [new PageBreak()] }),
    ],
  };

  // ────────────────────────────────────────────
  //  SECTION 3: Agent Engineering & Configuration
  // ────────────────────────────────────────────
  const sec3 = {
    properties: { ...pageProps, type: SectionType.CONTINUOUS },
    headers: { default: defaultHeader },
    footers: { default: defaultFooter },
    children: [
      heading1("3. Agent Engineering & Configuration"),

      heading2("3.1 Multi-Model Strategy"),
      bodyPara("PharmaAgent Pro uses three Claude models, each selected for a specific role:"),
      makeTable(
        ["Model", "Role", "Why This Model", "Where Used"],
        [
          ["Claude Opus 4.6", "Primary reasoning", "Deepest reasoning for drug analysis, safety assessment", "All 4 sub-agents"],
          ["Claude Haiku 4.5", "Query classifier", "Fastest model for real-time routing (~100ms)", "Orchestrator classifier"],
          ["Claude Sonnet 4.6", "Managed Agent", "Balanced cost/quality for platform agent", "deploy_managed_agent.py"],
        ],
        [2000, 1800, 3060, 2500]
      ),
      bodyPara("**Cost Optimization:** By routing classification to Haiku ($0.80/M input) instead of Opus ($15/M input), classification costs are reduced by 95%."),

      heading2("3.2 Orchestrator Pattern"),
      bodyPara("The PharmaOrchestrator implements a hierarchical routing architecture. When a user query arrives, it is first sent to the Haiku 4.5 classifier which returns a domain classification with confidence score. If confidence >= 0.7 and the domain has an agent config, the query is routed to the specialized sub-agent. Otherwise, the main orchestrator agent handles it."),
      ...codeBlock(
`User Query -> Haiku Classifier -> {"domain": "drug_discovery", "confidence": 0.92}
  |
  confidence >= 0.7 ? YES -> Drug Discovery Agent (Opus 4.6 + Extended Thinking)
                      NO  -> Main Orchestrator Agent (all tools)`
      ),

      heading2("3.3 Sub-Agent Configuration"),
      makeTable(
        ["Agent", "System Prompt Focus", "Tools", "Extended Thinking"],
        [
          ["Drug Discovery", "Medicinal chemistry, ADMET, SAR", "drug_lookup, drug_interaction_check", "ON"],
          ["Clinical Trials", "Trial design, biostatistics, enrollment", "trial_search, adverse_event_search, safety_signal", "ON"],
          ["Regulatory", "FDA/ICH compliance, document generation", "generate_document + search tools", "OFF"],
          ["Safety", "Signal detection, pharmacovigilance", "safety_signal_analysis, adverse_event_search", "ON"],
        ],
        [1800, 2800, 2960, 1800]
      ),
      bodyPara("Sub-agents are lazy-loaded: only instantiated when their domain is first requested, reducing memory footprint."),

      heading2("3.4 Extended Thinking"),
      bodyPara("Extended thinking is selectively enabled for domains requiring complex reasoning. When enabled, Claude is given a 10,000-token budget to reason step-by-step before generating its response."),
      ...codeBlock(
`# In base_agent.py
if use_thinking:
    request_params["thinking"] = {
        "type": "enabled",
        "budget_tokens": 10000
    }`
      ),

      heading2("3.5 Prompt Caching Strategy"),
      bodyPara("The system uses Claude's prompt caching to dramatically reduce costs in multi-turn conversations. The core system prompt (~1500 tokens) is marked with cache_control: {'type': 'ephemeral'} for a 5-minute TTL. Memory context is injected after the cached block so it stays fresh."),
      makeTable(
        ["Request", "System Prompt Cost", "Savings"],
        [
          ["First request (cache MISS)", "$18.75/M tokens (cache write)", "Baseline"],
          ["Subsequent within 5 min (HIT)", "$1.50/M tokens (cache read)", "90% savings"],
        ],
        [3200, 3560, 2600]
      ),

      heading2("3.6 Skill Files"),
      bodyPara("Each domain has a SKILL.md file in .claude/skills/ providing deep domain expertise:"),
      makeTable(
        ["Skill File", "Topics Covered"],
        [
          ["drug-discovery/SKILL.md", "SAR analysis, ADMET, toxicophore flagging, Lipinski, lead optimization"],
          ["clinical-trials/SKILL.md", "Trial design, biostatistics, DSMB briefings, adaptive trials"],
          ["regulatory-docs/SKILL.md", "Document structure per FDA/ICH, regulatory pathways, submission timelines"],
          ["safety-monitoring/SKILL.md", "Signal detection, causality (WHO-UMC), Bradford Hill, benefit-risk"],
        ],
        [3200, 6160]
      ),
      new Paragraph({ children: [new PageBreak()] }),
    ],
  };

  // ────────────────────────────────────────────
  //  SECTION 4: Tool System Design
  // ────────────────────────────────────────────
  const sec4 = {
    properties: { ...pageProps, type: SectionType.CONTINUOUS },
    headers: { default: defaultHeader },
    footers: { default: defaultFooter },
    children: [
      heading1("4. Tool System Design"),

      heading2("4.1 Tool Inventory"),
      makeTable(
        ["Tool", "Input", "Output", "Data Source"],
        [
          ["drug_lookup", "query, field", "Compound profiles + Lipinski", "drugs_compound_library.json"],
          ["drug_interaction_check", "compound_names[]", "CYP interaction pairs + risk", "drugs_compound_library.json"],
          ["trial_search", "query, field", "Trial details + enrollment", "clinical_trials.json"],
          ["adverse_event_search", "compound, trial_id, filters", "AE records + summary stats", "adverse_events.json"],
          ["safety_signal_analysis", "compound_name", "Signal detection + SOC analysis", "adverse_events.json + clinical_trials.json"],
          ["generate_document", "doc_type, compound, fields", "Regulatory scaffold + metadata", "regulatory_templates.json"],
        ],
        [2200, 2200, 2400, 2560]
      ),

      heading2("4.2 Agentic Tool Loop"),
      bodyPara("The base agent implements an agentic tool loop (max 10 iterations) that allows Claude to call tools iteratively until it has enough data to synthesize a final response:"),
      ...codeBlock(
`Iteration 1: Claude calls drug_lookup(query="Nexavirin") -> compound data
Iteration 2: Claude calls safety_signal_analysis(compound_name="Nexavirin") -> signal data
Iteration 3: Claude calls adverse_event_search(compound_name="Nexavirin") -> AE records
Iteration 4: Claude synthesizes all data -> final response (stop_reason: end_turn)`
      ),
      bodyPara("Exit conditions: stop_reason != 'tool_use', or max 10 iterations reached."),

      heading2("4.3 Managed Agent Custom Tool Flow"),
      bodyPara("When deployed to platform.claude.com, custom tools execute locally on the client:"),
      new Paragraph({
        numbering: { reference: "numbers2", level: 0 },
        children: [textRun("Agent emits 'agent.custom_tool_use' event (name, input, id)")],
      }),
      new Paragraph({
        numbering: { reference: "numbers2", level: 0 },
        children: [textRun("Client executes tool locally against JSON datasets")],
      }),
      new Paragraph({
        numbering: { reference: "numbers2", level: 0 },
        children: [textRun("Session goes idle with stop_reason.type == 'requires_action'")],
      }),
      new Paragraph({
        numbering: { reference: "numbers2", level: 0 },
        children: [textRun("Client sends 'user.custom_tool_result' with custom_tool_use_id")],
      }),
      new Paragraph({
        numbering: { reference: "numbers2", level: 0 },
        children: [textRun("Agent resumes processing with tool result")],
      }),
      bodyPara("**Key point:** No pharma data is uploaded to the platform."),
      new Paragraph({ children: [new PageBreak()] }),
    ],
  };

  // ────────────────────────────────────────────
  //  SECTION 5: LLM Strategy & Data Retrieval
  // ────────────────────────────────────────────
  const sec5 = {
    properties: { ...pageProps, type: SectionType.CONTINUOUS },
    headers: { default: defaultHeader },
    footers: { default: defaultFooter },
    children: [
      heading1("5. LLM Strategy & Data Retrieval"),

      heading2("5.1 Tool-Based Retrieval (Not RAG)"),
      bodyPara("PharmaAgent Pro does NOT use a traditional RAG pipeline with vector embeddings. Instead, it uses a tool-based retrieval approach where Claude decides which tool to call, tools execute deterministic searches against structured JSON datasets, and Claude synthesizes the results."),
      makeTable(
        ["Factor", "Tool-Based (Our Approach)", "RAG with Embeddings"],
        [
          ["Data size", "4 focused JSON files (~50KB)", "Better for millions of docs"],
          ["Precision", "Exact field matching", "Semantic similarity (may miss)"],
          ["Transparency", "Claude names the tool it calls", "Retrieval is opaque"],
          ["Compliance", "Tool calls fully auditable", "Harder to audit"],
          ["Cost", "No embedding costs", "Requires embedding API"],
        ],
        [2000, 3680, 3680]
      ),
      bodyPara("**When RAG would be appropriate:** If the dataset grows to thousands of documents, a vector store would be added as an additional tool."),

      heading2("5.2 Memory Store"),
      bodyPara("The memory store provides persistent context across sessions using a local file-based store with automatic versioning."),
      ...codeBlock(
`store_root/
  index.json                 -- Master index
  memories/<hash>.json       -- Current state
  versions/<hash>/v1.json    -- Immutable version history`
      ),
      bodyPara("Before each LLM call, get_context_for_agent() searches for memories tagged with the active agent and injects them into the system prompt after the cached block."),

      heading2("5.3 Prompt Caching (API-Level)"),
      bodyPara("Prompt caching is a Claude API feature. The system prompt is written to cache on the first request and subsequent requests within 5 minutes read from cache at 90% savings. The usage tracker records cache_creation_tokens and cache_read_tokens separately."),
      new Paragraph({ children: [new PageBreak()] }),
    ],
  };

  // ────────────────────────────────────────────
  //  SECTION 6: Environment & Session Management
  // ────────────────────────────────────────────
  const sec6 = {
    properties: { ...pageProps, type: SectionType.CONTINUOUS },
    headers: { default: defaultHeader },
    footers: { default: defaultFooter },
    children: [
      heading1("6. Environment & Session Management"),

      heading2("6.1 Managed Agent Environment"),
      bodyPara("The deployment creates a cloud environment on platform.claude.com with pip packages (pandas, jinja2, rich) and unrestricted networking."),

      heading2("6.2 Session Lifecycle"),
      ...codeBlock(
`Create Session -> status_idle (end_turn)
  -> User sends message -> status_running
    -> agent.thinking -> agent.message -> agent.custom_tool_use
    -> status_idle (requires_action) -> Client sends tool result
    -> status_running (resumes) -> agent.message
    -> status_idle (end_turn) -> Ready for next message`
      ),

      heading2("6.3 Local Session Management"),
      bodyPara("The local API server maintains per-session orchestrator instances. Each session has independent conversation history, sub-agent instances, memory context, and usage tracking."),
      new Paragraph({ children: [new PageBreak()] }),
    ],
  };

  // ────────────────────────────────────────────
  //  SECTION 7: Multi-Turn Conversation & Reuse
  // ────────────────────────────────────────────
  const sec7 = {
    properties: { ...pageProps, type: SectionType.CONTINUOUS },
    headers: { default: defaultHeader },
    footers: { default: defaultFooter },
    children: [
      heading1("7. Multi-Turn Conversation & Reuse"),

      heading2("7.1 Conversation Context Retention"),
      bodyPara("Multi-turn conversation is fully enabled. The full message history is maintained and sent with every API call. Claude naturally resolves references like 'its', 'that compound' from prior turns."),
      ...codeBlock(
`Turn 1: "Tell me about Nexavirin" -> drug_lookup -> Messages: [user_1, asst_1]
Turn 2: "What are its CYP interactions?" -> 'its' resolves to Nexavirin
Turn 3: "Compare that with Oncolytin-B" -> full context from prior turns`
      ),

      heading2("7.2 How Similar Questions Benefit"),
      bodyPara("When a user asks follow-up or similar questions, the system benefits in three ways:"),
      new Paragraph({
        numbering: { reference: "bullets", level: 0 },
        children: [textRun("Conversation History:", { bold: true }), textRun(" Prior tool results already in message history. Claude references without re-calling tools.")],
      }),
      new Paragraph({
        numbering: { reference: "bullets", level: 0 },
        children: [textRun("Prompt Cache Hits:", { bold: true }), textRun(" System prompt cached for 5 minutes. Follow-ups reuse cache, ~90% cost savings.")],
      }),
      new Paragraph({
        numbering: { reference: "bullets", level: 0 },
        children: [textRun("Memory Store:", { bold: true }), textRun(" Key findings saved to memory; subsequent sessions retrieve that context automatically.")],
      }),

      heading2("7.3 Session Reset"),
      bodyPara("Users can reset conversation history without losing memory using /reset (CLI) or POST /reset (API). This clears self.messages but preserves the memory store and audit trail."),
      new Paragraph({ children: [new PageBreak()] }),
    ],
  };

  // ────────────────────────────────────────────
  //  SECTION 8: Guardrails & Compliance
  // ────────────────────────────────────────────
  const sec8 = {
    properties: { ...pageProps, type: SectionType.CONTINUOUS },
    headers: { default: defaultHeader },
    footers: { default: defaultFooter },
    children: [
      heading1("8. Guardrails & Compliance"),

      heading2("8.1 Guardrail Pipeline"),
      bodyPara("Every request passes through a four-stage guardrail pipeline:"),
      ...codeBlock(
`INPUT -> [1] Rate Limiter (30 req/min)
      -> [2] Input Validator (PII + injection + prohibited topics)
      -> [3] LLM Processing (Claude + tools)
      -> [4] Output Filter (PII redaction + warnings + compliance footer)
      -> OUTPUT`
      ),

      heading2("8.2 PII Handling"),
      makeTable(
        ["PII Type", "Pattern", "Replacement"],
        [
          ["SSN", "XXX-XX-XXXX", "[REDACTED_SSN]"],
          ["Email", "Standard email regex", "[REDACTED_EMAIL]"],
          ["Phone", "XXX-XXX-XXXX", "[REDACTED_PHONE]"],
          ["Medical Record #", "MRN followed by digits", "[REDACTED_MRN]"],
          ["Date of Birth", "DOB followed by date", "[REDACTED_DOB]"],
          ["Credit Card", "XXXX-XXXX-XXXX-XXXX", "[REDACTED_CC]"],
        ],
        [2400, 3480, 3480]
      ),
      bodyPara("**Guarantee:** PII is redacted before being sent to the Claude API and again after response generation."),

      heading2("8.3 Compliance Validation"),
      makeTable(
        ["Document Type", "Standard", "Validates"],
        [
          ["IND Annual Report", "21 CFR 312.33", "ind_number, sponsor, 8 required sections"],
          ["Clinical Study Report", "ICH E3", "study_id, phase, 10 required sections"],
          ["CIOMS Safety Report", "ICH E2A", "ae_id, event_term, 4 required sections"],
          ["DSUR", "ICH E2F", "development_phase, DIBD, 8 required sections"],
          ["Investigator's Brochure", "ICH E6(R2)", "version, date, 5 required sections"],
        ],
        [2600, 2200, 4560]
      ),
      new Paragraph({ children: [new PageBreak()] }),
    ],
  };

  // ────────────────────────────────────────────
  //  SECTION 9: Development Process
  // ────────────────────────────────────────────
  const sec9 = {
    properties: { ...pageProps, type: SectionType.CONTINUOUS },
    headers: { default: defaultHeader },
    footers: { default: defaultFooter },
    children: [
      heading1("9. Development Process"),

      heading2("9.1 Setup"),
      ...codeBlock(
`git clone <repo-url> && cd ClaudeManagedAgentApp
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # Set ANTHROPIC_API_KEY`
      ),

      heading2("9.2 Testing"),
      bodyPara("The test suite contains 71+ tests across 4 files (no API key needed for unit tests):"),
      makeTable(
        ["Test File", "Count", "Coverage"],
        [
          ["test_tools.py", "30+", "All 6 tools: lookup, interaction, search, AE, signal, document"],
          ["test_guardrails.py", "20+", "Input validation, output filtering, compliance, rate limiting"],
          ["test_memory.py", "10+", "Write/read, versioning, search, tags, agent context"],
          ["test_utils.py", "15+", "Config, audit logger, usage tracker, cost calculation"],
        ],
        [2400, 1200, 5760]
      ),

      heading2("9.3 Local Development Modes"),
      makeTable(
        ["Mode", "Command", "Description"],
        [
          ["Interactive CLI", "python -m src.main", "Multi-turn chat with slash commands"],
          ["API Server", "python -m src.main --mode api", "FastAPI on port 8000 with /docs"],
          ["Managed Agent (Terminal)", "python deploy/chatbot.py", "Connects to platform.claude.com"],
          ["Managed Agent (Web)", "python deploy/chatbot_server.py", "Web UI on port 3000"],
        ],
        [2400, 2800, 4160]
      ),
      new Paragraph({ children: [new PageBreak()] }),
    ],
  };

  // ────────────────────────────────────────────
  //  SECTION 10: Deployment Process
  // ────────────────────────────────────────────
  const sec10 = {
    properties: { ...pageProps, type: SectionType.CONTINUOUS },
    headers: { default: defaultHeader },
    footers: { default: defaultFooter },
    children: [
      heading1("10. Deployment Process"),

      heading2("10.1 Deployment Sequence"),
      bodyPara("The deployment to platform.claude.com follows a 4-step process:"),
      new Paragraph({
        numbering: { reference: "numbers3", level: 0 },
        children: [textRun("Step 1: Create Agent", { bold: true }), textRun(" -- POST /v1/agents with name, model (Sonnet 4.6), system prompt, built-in toolset + 6 custom tools")],
      }),
      new Paragraph({
        numbering: { reference: "numbers3", level: 0 },
        children: [textRun("Step 2: Create Environment", { bold: true }), textRun(" -- POST /v1/environments with cloud type, pip packages, unrestricted networking")],
      }),
      new Paragraph({
        numbering: { reference: "numbers3", level: 0 },
        children: [textRun("Step 3: Create Memory Store", { bold: true }), textRun(" -- POST /v1/memory_stores, seed with pharma context. Currently research preview, gracefully degraded.")],
      }),
      new Paragraph({
        numbering: { reference: "numbers3", level: 0 },
        children: [textRun("Step 4: Create Session", { bold: true }), textRun(" -- POST /v1/sessions linking agent_id + environment_id. Optionally attaches memory_store.")],
      }),
      bodyPara("State is persisted to deploy_state.json with all resource IDs. The script is idempotent."),

      heading2("10.2 Running the Deployment"),
      ...codeBlock(
`export ANTHROPIC_API_KEY=sk-ant-...
python deploy/deploy_managed_agent.py    # Deploy (idempotent)
python deploy/chatbot.py                 # Terminal chatbot
python deploy/chatbot_server.py          # Web UI at http://localhost:3000`
      ),

      heading2("10.3 Architecture"),
      bodyPara("Custom tools execute locally on the client. The managed agent sends tool call requests; the client executes them against local datasets and returns results. No pharma data is uploaded to the platform."),
      new Paragraph({ children: [new PageBreak()] }),
    ],
  };

  // ────────────────────────────────────────────
  //  SECTION 11: Process Flow Diagrams
  // ────────────────────────────────────────────
  const sec11 = {
    properties: { ...pageProps, type: SectionType.CONTINUOUS },
    headers: { default: defaultHeader },
    footers: { default: defaultFooter },
    children: [
      heading1("11. Process Flow Diagrams"),

      heading2("11.1 End-to-End Request Flow"),
      ...codeBlock(
`User: "Run safety signal analysis on Oncolytin-B"
  |
  [Rate Limiter] PASS (23 remaining)
  [Input Validator] PII: none, Injection: clean
  |
  [Orchestrator] -> Haiku Classifier
    {"domain": "safety", "confidence": 0.95}
    Route: Safety Agent (Opus 4.6 + Thinking)
  |
  [Safety Agent] -> API Call #1
    Calls: safety_signal_analysis("Oncolytin-B")
    Result: ALERT (ILD signal, 2 SAEs)
  |
  [Safety Agent] -> API Call #2
    Calls: adverse_event_search(serious_only=true)
    Result: 2 SAE records with narratives
  |
  [Safety Agent] -> API Call #3
    Synthesizes final response (end_turn)
  |
  [Output Filter] 0 redactions, compliance footer
  [Audit Logger] query + 2 tool_use + response
  [Usage Tracker] ~5000 input tokens, ~$0.19`
      ),

      heading2("11.2 Managed Agent Custom Tool Flow"),
      ...codeBlock(
`Client                              Platform
  |                                      |
  | -- user.message ------------------>  |
  |                                      | Agent processes
  | <-- agent.custom_tool_use ---------- | (drug_lookup, id=evt_abc)
  |                                      |
  Execute tool locally                   |
  | <-- session.status_idle ------------ | requires_action
  |                                      |
  | -- user.custom_tool_result -------> |
  |    custom_tool_use_id: "evt_abc"     |
  |                                      | Agent resumes
  | <-- agent.message ------------------ | Final response
  | <-- session.status_idle ------------ | end_turn`
      ),
      new Paragraph({ children: [new PageBreak()] }),
    ],
  };

  // ────────────────────────────────────────────
  //  SECTION 12: FAQ & Troubleshooting
  // ────────────────────────────────────────────
  const sec12 = {
    properties: { ...pageProps, type: SectionType.CONTINUOUS },
    headers: { default: defaultHeader },
    footers: { default: defaultFooter },
    children: [
      heading1("12. FAQ & Troubleshooting"),

      heading2("Frequently Asked Questions"),

      new Paragraph({
        spacing: { before: 200, after: 60 },
        children: [textRun("Q: Does PharmaAgent Pro use RAG?", { bold: true })],
      }),
      bodyPara("A: No. It uses tool-based retrieval where Claude decides which tool to call, and tools execute deterministic searches against structured JSON datasets."),

      new Paragraph({
        spacing: { before: 200, after: 60 },
        children: [textRun("Q: Is patient data sent to Claude?", { bold: true })],
      }),
      bodyPara("A: No. PII is detected and redacted at the input boundary before any API call. Output is also filtered."),

      new Paragraph({
        spacing: { before: 200, after: 60 },
        children: [textRun("Q: How does multi-turn context work?", { bold: true })],
      }),
      bodyPara("A: Full conversation history is maintained in self.messages and sent with every API call."),

      new Paragraph({
        spacing: { before: 200, after: 60 },
        children: [textRun("Q: Why Sonnet for the managed agent instead of Opus?", { bold: true })],
      }),
      bodyPara("A: The managed agent handles general orchestration. Complex reasoning happens in local sub-agents (Opus)."),

      new Paragraph({
        spacing: { before: 200, after: 60 },
        children: [textRun("Q: How are costs controlled?", { bold: true })],
      }),
      bodyPara("A: Three mechanisms: (1) Haiku for classification, (2) prompt caching, (3) rate limiting."),

      heading2("Common Errors"),
      makeTable(
        ["Error", "Cause", "Fix"],
        [
          ["ANTHROPIC_API_KEY not set", "Missing .env", "Set key in .env file"],
          ["tool_use_id: Extra inputs not permitted", "Wrong field name", "Use custom_tool_use_id"],
          ["Rate limit exceeded", "Too many requests", "Wait or increase limit"],
          ["Session terminated", "Session expired", "Create new session"],
          ["Memory Store API not available", "Research preview", "Expected -- uses local fallback"],
        ],
        [3200, 2400, 3760]
      ),
      new Paragraph({ children: [new PageBreak()] }),
    ],
  };

  // ────────────────────────────────────────────
  //  SECTION 13: Roadmap
  // ────────────────────────────────────────────
  const sec13 = {
    properties: { ...pageProps, type: SectionType.CONTINUOUS },
    headers: { default: defaultHeader },
    footers: { default: defaultFooter },
    children: [
      heading1("13. Roadmap"),

      heading2("Phase 1: Foundation Hardening (Current + 2 Months)"),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [textRun("Vector Search Integration", { bold: true }), textRun(" -- Embedding-based retrieval for large document corpora")] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [textRun("Streaming Responses", { bold: true }), textRun(" -- Token-by-token streaming in CLI and Web UI")] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [textRun("Session Persistence", { bold: true }), textRun(" -- Conversation history saved to disk")] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [textRun("Managed Agent Memory Store", { bold: true }), textRun(" -- Adopt platform API when available")] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [textRun("Error Recovery", { bold: true }), textRun(" -- Retry logic with exponential backoff")] }),

      heading2("Phase 2: Multi-Agent Orchestration (Months 3-5)"),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [textRun("Parallel Agent Execution", { bold: true }), textRun(" -- Run drug_discovery + safety agents concurrently")] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [textRun("Agent-to-Agent Communication", { bold: true }), textRun(" -- Safety agent requests data from clinical trials agent")] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [textRun("Supervisor Agent", { bold: true }), textRun(" -- Meta-agent reviews sub-agent outputs for consistency")] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [textRun("Dynamic Tool Discovery", { bold: true }), textRun(" -- Agents request tools from other agents at runtime")] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [textRun("Conflict Resolution", { bold: true }), textRun(" -- Escalate disagreements to supervisor agent")] }),

      heading2("Phase 3: Enterprise Features (Months 6-9)"),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [textRun("Role-Based Access Control", { bold: true }), textRun(" -- Different tool permissions per role")] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [textRun("Real-Time Data Connectors", { bold: true }), textRun(" -- FDA FAERS, ClinicalTrials.gov, PubMed APIs")] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [textRun("Document Versioning & Approval Workflows")] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [textRun("Multi-Tenant Support", { bold: true }), textRun(" -- Isolated memory, audit, sessions per org")] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [textRun("Scheduled Monitoring", { bold: true }), textRun(" -- Automated daily safety scans with alerting")] }),

      heading2("Phase 4: Advanced Intelligence (Months 9-12)"),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [textRun("Literature-Augmented Analysis", { bold: true }), textRun(" -- RAG over biomedical literature")] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [textRun("Predictive Safety Modeling", { bold: true }), textRun(" -- Predict signals from historical AE data")] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [textRun("Automated Regulatory Submission Prep", { bold: true }), textRun(" -- End-to-end IND/NDA assembly")] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [textRun("Multi-Modal Analysis", { bold: true }), textRun(" -- Molecular images, clinical charts, lab reports")] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [textRun("Federated Learning", { bold: true }), textRun(" -- Cross-org signal sharing without raw data")] }),

      heading2("Deployment Milestones"),
      makeTable(
        ["Milestone", "Target", "Description"],
        [
          ["MVP", "Done", "Local + managed agent, 6 tools, 4 agents"],
          ["CI/CD Pipeline", "Month 1", "GitHub Actions automated testing + deploy"],
          ["Staging Environment", "Month 2", "Pre-production validation"],
          ["Production", "Month 3", "Docker/K8s with monitoring + autoscaling"],
          ["SOC 2 Compliance", "Month 6", "Audit hardening, encryption, access logging"],
          ["GxP Validation", "Month 9", "21 CFR Part 11 for regulated use"],
        ],
        [2400, 1600, 5360]
      ),

      // Footer
      new Paragraph({ spacing: { before: 600 } }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        children: [textRun("-- End of Technical Guide --", { italics: true, color: GRAY })],
      }),
    ],
  };

  // ────────────────────────────────────────────
  //  BUILD DOCUMENT
  // ────────────────────────────────────────────
  const doc = new Document({
    styles: {
      default: {
        document: {
          run: { font: "Arial", size: 24, color: "000000" },
        },
      },
      paragraphStyles: [
        {
          id: "Heading1",
          name: "Heading 1",
          basedOn: "Normal",
          next: "Normal",
          quickFormat: true,
          run: { size: 32, bold: true, font: "Arial", color: NAVY },
          paragraph: { spacing: { before: 240, after: 240 }, outlineLevel: 0 },
        },
        {
          id: "Heading2",
          name: "Heading 2",
          basedOn: "Normal",
          next: "Normal",
          quickFormat: true,
          run: { size: 28, bold: true, font: "Arial", color: NAVY },
          paragraph: { spacing: { before: 180, after: 180 }, outlineLevel: 1 },
        },
        {
          id: "Heading3",
          name: "Heading 3",
          basedOn: "Normal",
          next: "Normal",
          quickFormat: true,
          run: { size: 24, bold: true, font: "Arial", color: NAVY },
          paragraph: { spacing: { before: 120, after: 120 }, outlineLevel: 2 },
        },
      ],
    },
    numbering: {
      config: [
        {
          reference: "bullets",
          levels: [
            {
              level: 0,
              format: LevelFormat.BULLET,
              text: "\u2022",
              alignment: AlignmentType.LEFT,
              style: { paragraph: { indent: { left: 720, hanging: 360 } } },
            },
          ],
        },
        {
          reference: "numbers",
          levels: [
            {
              level: 0,
              format: LevelFormat.DECIMAL,
              text: "%1.",
              alignment: AlignmentType.LEFT,
              style: { paragraph: { indent: { left: 720, hanging: 360 } } },
            },
          ],
        },
        {
          reference: "numbers2",
          levels: [
            {
              level: 0,
              format: LevelFormat.DECIMAL,
              text: "%1.",
              alignment: AlignmentType.LEFT,
              style: { paragraph: { indent: { left: 720, hanging: 360 } } },
            },
          ],
        },
        {
          reference: "numbers3",
          levels: [
            {
              level: 0,
              format: LevelFormat.DECIMAL,
              text: "%1.",
              alignment: AlignmentType.LEFT,
              style: { paragraph: { indent: { left: 720, hanging: 360 } } },
            },
          ],
        },
      ],
    },
    sections: [
      coverSection,
      tocSection,
      sec1,
      sec2,
      sec3,
      sec4,
      sec5,
      sec6,
      sec7,
      sec8,
      sec9,
      sec10,
      sec11,
      sec12,
      sec13,
    ],
  });

  return doc;
}

// ── Main ──
async function main() {
  const doc = buildDoc();
  const buffer = await Packer.toBuffer(doc);
  const outPath = path.join(__dirname, "PharmaAgent_Pro_Technical_Guide.docx");
  fs.writeFileSync(outPath, buffer);
  console.log(`Document written to ${outPath} (${buffer.length} bytes)`);
}

main().catch((err) => {
  console.error("Error:", err);
  process.exit(1);
});
