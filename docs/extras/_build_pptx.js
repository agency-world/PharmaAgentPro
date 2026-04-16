const pptxgen = require("pptxgenjs");
const path = require("path");

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.3" x 7.5"
pres.author = "PharmaAgent Pro";
pres.title = "PharmaAgent Pro — Marketing Deck";

// ── Color palette ──
const C = {
  bg: "0F172A",
  surface: "1E293B",
  blue: "3B82F6",
  cyan: "06B6D4",
  green: "10B981",
  amber: "F59E0B",
  red: "EF4444",
  white: "FFFFFF",
  light: "E2E8F0",
  dim: "94A3B8",
  navy: "1A365D",
};

// ── Slide width constant ──
const SW = 13.3;
const SH = 7.5;

// ============================================================
// SLIDE 1: TITLE
// ============================================================
(function () {
  const slide = pres.addSlide();
  slide.background = { color: C.bg };

  // Blue rectangle with "P"
  slide.addShape(pres.shapes.RECTANGLE, {
    x: (SW - 1.2) / 2, y: 1.2, w: 1.2, h: 1.2,
    fill: { color: C.blue },
  });
  slide.addText("P", {
    x: (SW - 1.2) / 2, y: 1.2, w: 1.2, h: 1.2,
    fontSize: 48, fontFace: "Arial Black", color: C.white,
    bold: true, align: "center", valign: "middle",
  });

  // Title
  slide.addText("PharmaAgent Pro", {
    x: 0.5, y: 2.7, w: SW - 1, h: 0.8,
    fontSize: 44, fontFace: "Arial Black", color: C.white,
    bold: true, align: "center", valign: "middle",
  });

  // Subtitle
  slide.addText("Accelerating Drug Development with Agentic AI", {
    x: 0.5, y: 3.5, w: SW - 1, h: 0.6,
    fontSize: 22, fontFace: "Arial", color: C.cyan,
    align: "center", valign: "middle",
  });

  // Built on Claude
  slide.addText("Built on Claude's Managed Agent Platform", {
    x: 0.5, y: 4.2, w: SW - 1, h: 0.5,
    fontSize: 16, fontFace: "Calibri", color: C.dim,
    align: "center", valign: "middle",
  });

  // Confidential
  slide.addText("Confidential | April 2026", {
    x: 0.5, y: 6.5, w: SW - 1, h: 0.4,
    fontSize: 12, fontFace: "Calibri", color: C.dim,
    align: "center", valign: "middle",
  });
})();

// ============================================================
// SLIDE 2: THE PROBLEM
// ============================================================
(function () {
  const slide = pres.addSlide();
  slide.background = { color: C.bg };

  // Title
  slide.addText("The Problem: Drug Development Is Broken", {
    x: 0.5, y: 0.3, w: 10, h: 0.7,
    fontSize: 36, fontFace: "Arial Black", color: C.white,
    bold: true, align: "left", valign: "middle",
  });

  // Subtitle callout
  slide.addText("$2.6 Billion & 12 Years to bring a drug to market", {
    x: 0.5, y: 1.05, w: 10, h: 0.45,
    fontSize: 18, fontFace: "Calibri", color: C.amber,
    align: "left", valign: "middle",
  });

  // 6 pipeline stage cards
  const stages = [
    { name: "Compound\nDiscovery", dur: "3-6 yr", count: "10,000", borderColor: C.blue, textColor: C.blue },
    { name: "Preclinical", dur: "1-2 yr", count: "250", borderColor: C.blue, textColor: C.blue },
    { name: "Phase I", dur: "1-3 yr", count: "5", borderColor: C.blue, textColor: C.blue },
    { name: "Phase II", dur: "2-3 yr", count: "", borderColor: C.blue, textColor: C.blue },
    { name: "Phase III", dur: "1-2 yr", count: "1", borderColor: C.blue, textColor: C.blue },
    { name: "FDA Review", dur: "1-2 yr", count: "1 APPROVED", borderColor: C.green, textColor: C.green },
  ];

  const stageW = 1.85;
  const stageGap = 0.18;
  const totalStageW = stages.length * stageW + (stages.length - 1) * stageGap;
  const stageStartX = (SW - totalStageW) / 2;
  const stageY = 1.65;
  const stageH = 1.25;

  stages.forEach((s, i) => {
    const sx = stageStartX + i * (stageW + stageGap);
    slide.addShape(pres.shapes.RECTANGLE, {
      x: sx, y: stageY, w: stageW, h: stageH,
      fill: { color: C.surface },
      line: { color: s.borderColor, width: 1.5 },
    });
    slide.addText([
      { text: s.name, options: { fontSize: 11, fontFace: "Calibri", color: s.textColor, bold: true, breakLine: true } },
      { text: s.dur, options: { fontSize: 10, fontFace: "Calibri", color: C.dim, breakLine: true } },
      { text: s.count, options: { fontSize: 9, fontFace: "Calibri", color: C.light } },
    ], {
      x: sx + 0.08, y: stageY + 0.1, w: stageW - 0.16, h: stageH - 0.2,
      align: "center", valign: "middle",
    });
  });

  // 5 problem cards
  const problems = [
    { title: "Data Silos", body: "Fragmented data across systems" },
    { title: "Manual Documents", body: "Weeks of manual report writing" },
    { title: "Delayed Safety", body: "Slow adverse event detection" },
    { title: "Knowledge Gaps", body: "Critical insights lost between teams" },
    { title: "Compliance Burden", body: "Regulatory overhead slowing progress" },
  ];

  const probW = 2.25;
  const probGap = 0.18;
  const totalProbW = problems.length * probW + (problems.length - 1) * probGap;
  const probStartX = (SW - totalProbW) / 2;
  const probY = 3.15;
  const probH = 1.2;

  problems.forEach((p, i) => {
    const px = probStartX + i * (probW + probGap);
    slide.addShape(pres.shapes.RECTANGLE, {
      x: px, y: probY, w: probW, h: probH,
      fill: { color: C.surface },
      line: { color: C.red, width: 1.5 },
    });
    slide.addText([
      { text: p.title, options: { fontSize: 13, fontFace: "Calibri", color: C.red, bold: true, breakLine: true } },
      { text: p.body, options: { fontSize: 10, fontFace: "Calibri", color: C.dim } },
    ], {
      x: px + 0.1, y: probY + 0.1, w: probW - 0.2, h: probH - 0.2,
      align: "center", valign: "middle",
    });
  });

  // Bottom section
  slide.addText("The Cost of Delay", {
    x: 0.5, y: 4.65, w: 6, h: 0.5,
    fontSize: 18, fontFace: "Calibri", color: C.white,
    bold: true, align: "left", valign: "middle",
  });

  slide.addText([
    { text: "Every month of delay = $30-100M in lost revenue", options: { bullet: true, breakLine: true, fontSize: 14, fontFace: "Calibri", color: C.light } },
    { text: "Late-stage failures from missed signals = $800M-1.5B wasted", options: { bullet: true, breakLine: true, fontSize: 14, fontFace: "Calibri", color: C.light } },
    { text: "FDA rejection from incomplete submissions = 6-12 months rework", options: { bullet: true, fontSize: 14, fontFace: "Calibri", color: C.light } },
  ], {
    x: 0.5, y: 5.15, w: 12, h: 1.8,
    valign: "top",
  });
})();

// ============================================================
// SLIDE 3: THE SOLUTION
// ============================================================
(function () {
  const slide = pres.addSlide();
  slide.background = { color: C.bg };

  // Title
  slide.addText("The Solution: PharmaAgent Pro", {
    x: 0.5, y: 0.3, w: 10, h: 0.7,
    fontSize: 36, fontFace: "Arial Black", color: C.white,
    bold: true, align: "left", valign: "middle",
  });

  // Subtitle
  slide.addText("An AI agent that thinks like your best researcher", {
    x: 0.5, y: 1.0, w: 10, h: 0.4,
    fontSize: 18, fontFace: "Arial", color: C.cyan,
    align: "left", valign: "middle",
  });

  // Workflow demo box
  const demoX = 0.5;
  const demoY = 1.6;
  const demoW = 12.3;
  const demoH = 2.6;

  slide.addShape(pres.shapes.RECTANGLE, {
    x: demoX, y: demoY, w: demoW, h: demoH,
    fill: { color: C.surface },
    line: { color: C.cyan, width: 1.5 },
  });

  slide.addText([
    { text: "User: \"Analyze Oncolytin-B safety profile and generate a CIOMS report\"", options: { fontSize: 12, fontFace: "Calibri", color: C.light, bold: true, breakLine: true } },
    { text: "", options: { fontSize: 6, breakLine: true } },
    { text: "1. Classify query -> Safety + Regulatory domain", options: { fontSize: 11, fontFace: "Calibri", color: C.cyan, breakLine: true } },
    { text: "2. Run safety_signal_analysis tool -> 3 AEs, 2 SAEs detected", options: { fontSize: 11, fontFace: "Calibri", color: C.cyan, breakLine: true } },
    { text: "3. Flag ILD (Interstitial Lung Disease) -> ALERT status", options: { fontSize: 11, fontFace: "Calibri", color: C.amber, breakLine: true } },
    { text: "4. Run adverse_event_search -> Detailed SAE records retrieved", options: { fontSize: 11, fontFace: "Calibri", color: C.cyan, breakLine: true } },
    { text: "5. Run generate_document -> ICH E2A CIOMS I form generated", options: { fontSize: 11, fontFace: "Calibri", color: C.cyan, breakLine: true } },
    { text: "", options: { fontSize: 6, breakLine: true } },
    { text: "Complete analysis + CIOMS report in < 60 seconds", options: { fontSize: 12, fontFace: "Calibri", color: C.green, bold: true, breakLine: true } },
    { text: "(Previously: 2-3 days)", options: { fontSize: 11, fontFace: "Calibri", color: C.dim } },
  ], {
    x: demoX + 0.3, y: demoY + 0.15, w: demoW - 0.6, h: demoH - 0.3,
    valign: "top",
  });

  // 4 agent cards
  const agents = [
    { name: "Drug Discovery Agent", desc: "Compound profiling, drug-likeness, CYP interactions, SAR", metric: "10x faster screening" },
    { name: "Clinical Trials Agent", desc: "Trial status, enrollment, endpoint analysis, interim results", metric: "Real-time intelligence" },
    { name: "Regulatory Agent", desc: "FDA/ICH-compliant document generation (IND, CSR, CIOMS)", metric: "80% less prep time" },
    { name: "Safety Agent", desc: "AE analysis, signal detection, benefit-risk assessment", metric: "Seconds, not weeks" },
  ];

  const agentW = 2.9;
  const agentGap = 0.2;
  const totalAgentW = agents.length * agentW + (agents.length - 1) * agentGap;
  const agentStartX = (SW - totalAgentW) / 2;
  const agentY = 4.5;
  const agentH = 2.5;

  agents.forEach((a, i) => {
    const ax = agentStartX + i * (agentW + agentGap);
    slide.addShape(pres.shapes.RECTANGLE, {
      x: ax, y: agentY, w: agentW, h: agentH,
      fill: { color: C.surface },
      line: { color: C.blue, width: 1.5 },
    });
    slide.addText([
      { text: a.name, options: { fontSize: 14, fontFace: "Calibri", color: C.white, bold: true, breakLine: true } },
      { text: "", options: { fontSize: 6, breakLine: true } },
      { text: a.desc, options: { fontSize: 11, fontFace: "Calibri", color: C.dim, breakLine: true } },
      { text: "", options: { fontSize: 8, breakLine: true } },
      { text: a.metric, options: { fontSize: 12, fontFace: "Calibri", color: C.green, bold: true } },
    ], {
      x: ax + 0.15, y: agentY + 0.15, w: agentW - 0.3, h: agentH - 0.3,
      valign: "top",
    });
  });
})();

// ============================================================
// SLIDE 4: HOW IT WORKS
// ============================================================
(function () {
  const slide = pres.addSlide();
  slide.background = { color: C.bg };

  // Title
  slide.addText("How It Works: Intelligent Query Routing", {
    x: 0.5, y: 0.3, w: 10, h: 0.7,
    fontSize: 36, fontFace: "Arial Black", color: C.white,
    bold: true, align: "left", valign: "middle",
  });

  // Left side: 5 stacked flow cards
  const flowCards = [
    { label: "User Question", borderColor: C.light },
    { label: "AI Classifier (Haiku 4.5, <100ms)", borderColor: C.amber },
    { label: "Specialized Agent (Opus 4.6)", borderColor: C.blue },
    { label: "Tool Execution (Local Data)", borderColor: C.cyan },
    { label: "Synthesized Response", borderColor: C.green },
  ];

  const flowX = 0.5;
  const flowW = 4.5;
  const flowCardH = 0.7;
  const flowGap = 0.15;
  const arrowH = 0.3;
  let flowCurrY = 1.3;

  flowCards.forEach((fc, i) => {
    slide.addShape(pres.shapes.RECTANGLE, {
      x: flowX, y: flowCurrY, w: flowW, h: flowCardH,
      fill: { color: C.surface },
      line: { color: fc.borderColor, width: 1.5 },
    });
    slide.addText(fc.label, {
      x: flowX + 0.15, y: flowCurrY, w: flowW - 0.3, h: flowCardH,
      fontSize: 13, fontFace: "Calibri", color: C.white,
      bold: true, align: "center", valign: "middle",
    });
    flowCurrY += flowCardH;

    // Arrow between cards (not after last)
    if (i < flowCards.length - 1) {
      const arrowCenterX = flowX + flowW / 2;
      slide.addText("\u25BC", {
        x: arrowCenterX - 0.3, y: flowCurrY, w: 0.6, h: arrowH,
        fontSize: 16, fontFace: "Arial", color: C.dim,
        align: "center", valign: "middle",
      });
      flowCurrY += arrowH + flowGap;
    }
  });

  // Right side: Table - Key Technology Decisions
  const tableX = 5.5;
  const tableY = 1.3;
  const tableW = 7.3;

  slide.addText("Key Technology Decisions", {
    x: tableX, y: tableY, w: tableW, h: 0.5,
    fontSize: 20, fontFace: "Calibri", color: C.white,
    bold: true, align: "left", valign: "middle",
  });

  const techRows = [
    [
      { text: "Feature", options: { fill: { color: C.blue }, color: C.white, bold: true, fontSize: 11, fontFace: "Calibri" } },
      { text: "How It Works", options: { fill: { color: C.blue }, color: C.white, bold: true, fontSize: 11, fontFace: "Calibri" } },
      { text: "Why It Matters", options: { fill: { color: C.blue }, color: C.white, bold: true, fontSize: 11, fontFace: "Calibri" } },
    ],
    [
      { text: "Multi-Model AI", options: { fill: { color: C.surface }, color: C.light, fontSize: 10, fontFace: "Calibri" } },
      { text: "Haiku classifies, Opus reasons", options: { fill: { color: C.surface }, color: C.light, fontSize: 10, fontFace: "Calibri" } },
      { text: "Cost + speed optimized", options: { fill: { color: C.surface }, color: C.light, fontSize: 10, fontFace: "Calibri" } },
    ],
    [
      { text: "Extended Thinking", options: { fill: { color: "141E33" }, color: C.light, fontSize: 10, fontFace: "Calibri" } },
      { text: "Multi-step reasoning chains", options: { fill: { color: "141E33" }, color: C.light, fontSize: 10, fontFace: "Calibri" } },
      { text: "Complex drug interactions", options: { fill: { color: "141E33" }, color: C.light, fontSize: 10, fontFace: "Calibri" } },
    ],
    [
      { text: "Tool-Based Retrieval", options: { fill: { color: C.surface }, color: C.light, fontSize: 10, fontFace: "Calibri" } },
      { text: "6 specialized pharma tools", options: { fill: { color: C.surface }, color: C.light, fontSize: 10, fontFace: "Calibri" } },
      { text: "Accurate, grounded answers", options: { fill: { color: C.surface }, color: C.light, fontSize: 10, fontFace: "Calibri" } },
    ],
    [
      { text: "Prompt Caching", options: { fill: { color: "141E33" }, color: C.light, fontSize: 10, fontFace: "Calibri" } },
      { text: "Cache system prompts & tools", options: { fill: { color: "141E33" }, color: C.light, fontSize: 10, fontFace: "Calibri" } },
      { text: "90% cost reduction on repeats", options: { fill: { color: "141E33" }, color: C.light, fontSize: 10, fontFace: "Calibri" } },
    ],
    [
      { text: "Guardrails", options: { fill: { color: C.surface }, color: C.light, fontSize: 10, fontFace: "Calibri" } },
      { text: "Input/output validation + PII", options: { fill: { color: C.surface }, color: C.light, fontSize: 10, fontFace: "Calibri" } },
      { text: "Regulatory compliance", options: { fill: { color: C.surface }, color: C.light, fontSize: 10, fontFace: "Calibri" } },
    ],
  ];

  slide.addTable(techRows, {
    x: tableX, y: tableY + 0.55, w: tableW,
    colW: [2.0, 2.8, 2.5],
    border: { pt: 0.5, color: "334155" },
    margin: [4, 6, 4, 6],
  });
})();

// ============================================================
// SLIDE 5: PRODUCT SCREENSHOTS
// ============================================================
(function () {
  const slide = pres.addSlide();
  slide.background = { color: C.bg };

  // Title
  slide.addText("Product Experience", {
    x: 0.5, y: 0.3, w: 10, h: 0.7,
    fontSize: 36, fontFace: "Arial Black", color: C.white,
    bold: true, align: "left", valign: "middle",
  });

  // LEFT: Terminal Chat mockup
  const termX = 0.5;
  const termY = 1.3;
  const termW = 5.9;
  const termH = 5.5;

  slide.addShape(pres.shapes.RECTANGLE, {
    x: termX, y: termY, w: termW, h: termH,
    fill: { color: "1A1A2E" },
    line: { color: "334155", width: 1 },
  });

  slide.addText("Terminal Chat Interface", {
    x: termX + 0.2, y: termY + 0.1, w: termW - 0.4, h: 0.4,
    fontSize: 14, fontFace: "Calibri", color: C.cyan, bold: true,
  });

  slide.addText([
    { text: "PharmaAgent Pro -- Managed Agent Chatbot", options: { fontSize: 10, fontFace: "Courier New", color: C.dim, breakLine: true } },
    { text: "Type 'exit' to quit | Extended thinking enabled", options: { fontSize: 9, fontFace: "Courier New", color: C.dim, breakLine: true } },
    { text: "", options: { fontSize: 6, breakLine: true } },
    { text: "You > Which compounds target EGFR?", options: { fontSize: 11, fontFace: "Courier New", color: C.green, bold: true, breakLine: true } },
    { text: "", options: { fontSize: 6, breakLine: true } },
    { text: "(thinking...)", options: { fontSize: 10, fontFace: "Courier New", color: C.amber, breakLine: true } },
    { text: "Custom Tool: drug_lookup", options: { fontSize: 10, fontFace: "Courier New", color: C.cyan, breakLine: true } },
    { text: "", options: { fontSize: 6, breakLine: true } },
    { text: "Found 3 compounds targeting EGFR:", options: { fontSize: 10, fontFace: "Courier New", color: C.light, breakLine: true } },
    { text: "", options: { fontSize: 4, breakLine: true } },
    { text: "1. Oncolytin-B (ONC-201)", options: { fontSize: 10, fontFace: "Courier New", color: C.light, breakLine: true } },
    { text: "   Phase: Phase II | Status: Active", options: { fontSize: 10, fontFace: "Courier New", color: C.light, breakLine: true } },
    { text: "   Mechanism: EGFR/HER2 dual inhibitor", options: { fontSize: 10, fontFace: "Courier New", color: C.light, breakLine: true } },
    { text: "   Drug-likeness: 0.87 (Good)", options: { fontSize: 10, fontFace: "Courier New", color: C.light, breakLine: true } },
    { text: "", options: { fontSize: 4, breakLine: true } },
    { text: "2. Cetuximab-ADC (CTX-4892)", options: { fontSize: 10, fontFace: "Courier New", color: C.light, breakLine: true } },
    { text: "   Phase: Phase I | Status: Enrolling", options: { fontSize: 10, fontFace: "Courier New", color: C.light, breakLine: true } },
  ], {
    x: termX + 0.2, y: termY + 0.55, w: termW - 0.4, h: termH - 0.7,
    valign: "top",
  });

  // RIGHT: Web Chat mockup
  const webX = 6.9;
  const webY = 1.3;
  const webW = 5.9;
  const webH = 5.5;

  slide.addShape(pres.shapes.RECTANGLE, {
    x: webX, y: webY, w: webW, h: webH,
    fill: { color: C.bg },
    line: { color: "334155", width: 1 },
  });

  slide.addText("Web Chat Interface", {
    x: webX + 0.2, y: webY + 0.1, w: webW - 0.4, h: 0.4,
    fontSize: 14, fontFace: "Calibri", color: C.cyan, bold: true,
  });

  slide.addText([
    { text: "YOU", options: { fontSize: 11, fontFace: "Calibri", color: C.blue, bold: true, breakLine: true } },
    { text: "Analyze Oncolytin-B safety and generate CIOMS", options: { fontSize: 10, fontFace: "Calibri", color: C.light, breakLine: true } },
    { text: "", options: { fontSize: 8, breakLine: true } },
    { text: "PHARMAAGENT PRO", options: { fontSize: 11, fontFace: "Calibri", color: C.cyan, bold: true, breakLine: true } },
    { text: "[safety_signal_analysis] [adverse_event_search]", options: { fontSize: 10, fontFace: "Calibri", color: C.green, breakLine: true } },
    { text: "", options: { fontSize: 6, breakLine: true } },
    { text: "Safety Signal Analysis: Oncolytin-B", options: { fontSize: 12, fontFace: "Calibri", color: C.white, bold: true, breakLine: true } },
    { text: "", options: { fontSize: 4, breakLine: true } },
    { text: "Overall Signal Status: ALERT", options: { fontSize: 12, fontFace: "Calibri", color: C.red, bold: true, breakLine: true } },
    { text: "", options: { fontSize: 4, breakLine: true } },
    { text: "Total Adverse Events: 3", options: { fontSize: 10, fontFace: "Calibri", color: C.light, breakLine: true } },
    { text: "Serious Adverse Events: 2", options: { fontSize: 10, fontFace: "Calibri", color: C.light, breakLine: true } },
    { text: "ILD Signal: Grade 3 (Serious)", options: { fontSize: 10, fontFace: "Calibri", color: C.amber, breakLine: true } },
    { text: "QTc Prolongation: Grade 2", options: { fontSize: 10, fontFace: "Calibri", color: C.amber, breakLine: true } },
    { text: "", options: { fontSize: 6, breakLine: true } },
    { text: "Recommendation: Immediate DSMB review", options: { fontSize: 11, fontFace: "Calibri", color: C.red, bold: true } },
  ], {
    x: webX + 0.2, y: webY + 0.55, w: webW - 0.4, h: webH - 0.7,
    valign: "top",
  });
})();

// ============================================================
// SLIDE 6: BENEFITS & IMPACT
// ============================================================
(function () {
  const slide = pres.addSlide();
  slide.background = { color: C.bg };

  // Title
  slide.addText("Benefits & Potential Impact", {
    x: 0.5, y: 0.3, w: 10, h: 0.7,
    fontSize: 36, fontFace: "Arial Black", color: C.white,
    bold: true, align: "left", valign: "middle",
  });

  // ── Left top: Quantified Value table ──
  slide.addText("Quantified Value", {
    x: 0.5, y: 1.15, w: 6, h: 0.45,
    fontSize: 20, fontFace: "Calibri", color: C.white,
    bold: true, align: "left", valign: "middle",
  });

  const valRows = [
    [
      { text: "Task", options: { fill: { color: C.blue }, color: C.white, bold: true, fontSize: 10, fontFace: "Calibri" } },
      { text: "Before", options: { fill: { color: C.blue }, color: C.white, bold: true, fontSize: 10, fontFace: "Calibri" } },
      { text: "After", options: { fill: { color: C.blue }, color: C.white, bold: true, fontSize: 10, fontFace: "Calibri" } },
      { text: "Improvement", options: { fill: { color: C.blue }, color: C.white, bold: true, fontSize: 10, fontFace: "Calibri" } },
    ],
    [
      { text: "Safety Signal", options: { fill: { color: C.surface }, color: C.light, fontSize: 10, fontFace: "Calibri" } },
      { text: "2-4 weeks", options: { fill: { color: C.surface }, color: C.light, fontSize: 10, fontFace: "Calibri" } },
      { text: "<60s", options: { fill: { color: C.surface }, color: C.green, fontSize: 10, fontFace: "Calibri", bold: true } },
      { text: "99%", options: { fill: { color: C.surface }, color: C.green, fontSize: 10, fontFace: "Calibri", bold: true } },
    ],
    [
      { text: "CIOMS Report", options: { fill: { color: "141E33" }, color: C.light, fontSize: 10, fontFace: "Calibri" } },
      { text: "2-3 days", options: { fill: { color: "141E33" }, color: C.light, fontSize: 10, fontFace: "Calibri" } },
      { text: "<2 min", options: { fill: { color: "141E33" }, color: C.green, fontSize: 10, fontFace: "Calibri", bold: true } },
      { text: "99%", options: { fill: { color: "141E33" }, color: C.green, fontSize: 10, fontFace: "Calibri", bold: true } },
    ],
    [
      { text: "Interaction Check", options: { fill: { color: C.surface }, color: C.light, fontSize: 10, fontFace: "Calibri" } },
      { text: "4-6 hours", options: { fill: { color: C.surface }, color: C.light, fontSize: 10, fontFace: "Calibri" } },
      { text: "<30s", options: { fill: { color: C.surface }, color: C.green, fontSize: 10, fontFace: "Calibri", bold: true } },
      { text: "99%", options: { fill: { color: C.surface }, color: C.green, fontSize: 10, fontFace: "Calibri", bold: true } },
    ],
    [
      { text: "IND Report", options: { fill: { color: "141E33" }, color: C.light, fontSize: 10, fontFace: "Calibri" } },
      { text: "3-5 days", options: { fill: { color: "141E33" }, color: C.light, fontSize: 10, fontFace: "Calibri" } },
      { text: "10-15 min", options: { fill: { color: "141E33" }, color: C.green, fontSize: 10, fontFace: "Calibri", bold: true } },
      { text: "97%", options: { fill: { color: "141E33" }, color: C.green, fontSize: 10, fontFace: "Calibri", bold: true } },
    ],
  ];

  slide.addTable(valRows, {
    x: 0.5, y: 1.65, w: 6.3,
    colW: [1.7, 1.3, 1.3, 1.3],
    border: { pt: 0.5, color: "334155" },
    margin: [3, 5, 3, 5],
  });

  // ── Right top: Impact by Stakeholder ──
  slide.addText("Impact by Stakeholder", {
    x: 7.2, y: 1.15, w: 5.5, h: 0.45,
    fontSize: 20, fontFace: "Calibri", color: C.white,
    bold: true, align: "left", valign: "middle",
  });

  const stakeRows = [
    [
      { text: "Stakeholder", options: { fill: { color: C.blue }, color: C.white, bold: true, fontSize: 10, fontFace: "Calibri" } },
      { text: "Key Benefit", options: { fill: { color: C.blue }, color: C.white, bold: true, fontSize: 10, fontFace: "Calibri" } },
    ],
    [
      { text: "Medicinal Chemists", options: { fill: { color: C.surface }, color: C.light, fontSize: 10, fontFace: "Calibri" } },
      { text: "10x faster compound screening", options: { fill: { color: C.surface }, color: C.light, fontSize: 10, fontFace: "Calibri" } },
    ],
    [
      { text: "Clinical Ops", options: { fill: { color: "141E33" }, color: C.light, fontSize: 10, fontFace: "Calibri" } },
      { text: "Eliminate manual report cycles", options: { fill: { color: "141E33" }, color: C.light, fontSize: 10, fontFace: "Calibri" } },
    ],
    [
      { text: "Reg Affairs", options: { fill: { color: C.surface }, color: C.light, fontSize: 10, fontFace: "Calibri" } },
      { text: "80% less document prep time", options: { fill: { color: C.surface }, color: C.light, fontSize: 10, fontFace: "Calibri" } },
    ],
    [
      { text: "Pharmacovigilance", options: { fill: { color: "141E33" }, color: C.light, fontSize: 10, fontFace: "Calibri" } },
      { text: "Same-day signal detection", options: { fill: { color: "141E33" }, color: C.light, fontSize: 10, fontFace: "Calibri" } },
    ],
    [
      { text: "Medical Writing", options: { fill: { color: C.surface }, color: C.light, fontSize: 10, fontFace: "Calibri" } },
      { text: "Focus on content, not formatting", options: { fill: { color: C.surface }, color: C.light, fontSize: 10, fontFace: "Calibri" } },
    ],
    [
      { text: "Exec Leadership", options: { fill: { color: "141E33" }, color: C.light, fontSize: 10, fontFace: "Calibri" } },
      { text: "Data-driven portfolio decisions", options: { fill: { color: "141E33" }, color: C.light, fontSize: 10, fontFace: "Calibri" } },
    ],
  ];

  slide.addTable(stakeRows, {
    x: 7.2, y: 1.65, w: 5.6,
    colW: [2.0, 3.6],
    border: { pt: 0.5, color: "334155" },
    margin: [3, 5, 3, 5],
  });

  // ── Bottom: Safety & Compliance ──
  slide.addText("Safety & Compliance by Design", {
    x: 0.5, y: 4.7, w: 8, h: 0.45,
    fontSize: 20, fontFace: "Calibri", color: C.white,
    bold: true, align: "left", valign: "middle",
  });

  const safetyCards = [
    { title: "Zero PII Exposure", accent: C.green, body: "All PII redacted before any API call" },
    { title: "Full Audit Trail", accent: C.blue, body: "Immutable JSONL logging of every action" },
    { title: "FDA/ICH Validation", accent: C.cyan, body: "21 CFR 312, ICH E2A/E2F/E3 compliant" },
    { title: "Rate Limiting", accent: C.amber, body: "Per-user sliding window protection" },
  ];

  const scW = 2.85;
  const scGap = 0.2;
  const totalScW = safetyCards.length * scW + (safetyCards.length - 1) * scGap;
  const scStartX = (SW - totalScW) / 2;
  const scY = 5.3;
  const scH = 1.7;

  safetyCards.forEach((sc, i) => {
    const sx = scStartX + i * (scW + scGap);
    slide.addShape(pres.shapes.RECTANGLE, {
      x: sx, y: scY, w: scW, h: scH,
      fill: { color: C.surface },
      line: { color: sc.accent, width: 1.5 },
    });
    slide.addText([
      { text: sc.title, options: { fontSize: 14, fontFace: "Calibri", color: sc.accent, bold: true, breakLine: true } },
      { text: "", options: { fontSize: 6, breakLine: true } },
      { text: sc.body, options: { fontSize: 11, fontFace: "Calibri", color: C.dim } },
    ], {
      x: sx + 0.15, y: scY + 0.15, w: scW - 0.3, h: scH - 0.3,
      valign: "top",
    });
  });
})();

// ============================================================
// SLIDE 7: COMPETITIVE ADVANTAGE
// ============================================================
(function () {
  const slide = pres.addSlide();
  slide.background = { color: C.bg };

  // Title
  slide.addText("Why PharmaAgent Pro?", {
    x: 0.5, y: 0.3, w: 10, h: 0.7,
    fontSize: 36, fontFace: "Arial Black", color: C.white,
    bold: true, align: "left", valign: "middle",
  });

  // ── Left table: vs Generic AI Chatbots ──
  slide.addText("vs. General-Purpose AI Chatbots", {
    x: 0.5, y: 1.15, w: 6, h: 0.45,
    fontSize: 20, fontFace: "Calibri", color: C.white,
    bold: true, align: "left", valign: "middle",
  });

  const genRows = [
    [
      { text: "Capability", options: { fill: { color: C.blue }, color: C.white, bold: true, fontSize: 10, fontFace: "Calibri" } },
      { text: "Generic AI", options: { fill: { color: C.blue }, color: C.white, bold: true, fontSize: 10, fontFace: "Calibri" } },
      { text: "PharmaAgent Pro", options: { fill: { color: C.blue }, color: C.white, bold: true, fontSize: 10, fontFace: "Calibri" } },
    ],
    [
      { text: "Pharma Tools", options: { fill: { color: C.surface }, color: C.light, fontSize: 10, fontFace: "Calibri" } },
      { text: "None", options: { fill: { color: C.surface }, color: C.red, fontSize: 10, fontFace: "Calibri" } },
      { text: "6 specialized tools", options: { fill: { color: C.surface }, color: C.green, fontSize: 10, fontFace: "Calibri" } },
    ],
    [
      { text: "Regulatory Docs", options: { fill: { color: "141E33" }, color: C.light, fontSize: 10, fontFace: "Calibri" } },
      { text: "Generic text", options: { fill: { color: "141E33" }, color: C.red, fontSize: 10, fontFace: "Calibri" } },
      { text: "ICH-compliant templates", options: { fill: { color: "141E33" }, color: C.green, fontSize: 10, fontFace: "Calibri" } },
    ],
    [
      { text: "PII Protection", options: { fill: { color: C.surface }, color: C.light, fontSize: 10, fontFace: "Calibri" } },
      { text: "User responsibility", options: { fill: { color: C.surface }, color: C.red, fontSize: 10, fontFace: "Calibri" } },
      { text: "Auto-redaction layer", options: { fill: { color: C.surface }, color: C.green, fontSize: 10, fontFace: "Calibri" } },
    ],
    [
      { text: "Audit Trail", options: { fill: { color: "141E33" }, color: C.light, fontSize: 10, fontFace: "Calibri" } },
      { text: "Chat history only", options: { fill: { color: "141E33" }, color: C.red, fontSize: 10, fontFace: "Calibri" } },
      { text: "Full JSONL audit log", options: { fill: { color: "141E33" }, color: C.green, fontSize: 10, fontFace: "Calibri" } },
    ],
    [
      { text: "Extended Thinking", options: { fill: { color: C.surface }, color: C.light, fontSize: 10, fontFace: "Calibri" } },
      { text: "Limited", options: { fill: { color: C.surface }, color: C.red, fontSize: 10, fontFace: "Calibri" } },
      { text: "Multi-step reasoning", options: { fill: { color: C.surface }, color: C.green, fontSize: 10, fontFace: "Calibri" } },
    ],
    [
      { text: "Multi-Agent", options: { fill: { color: "141E33" }, color: C.light, fontSize: 10, fontFace: "Calibri" } },
      { text: "Single model", options: { fill: { color: "141E33" }, color: C.red, fontSize: 10, fontFace: "Calibri" } },
      { text: "4 domain specialists", options: { fill: { color: "141E33" }, color: C.green, fontSize: 10, fontFace: "Calibri" } },
    ],
    [
      { text: "Cost Tracking", options: { fill: { color: C.surface }, color: C.light, fontSize: 10, fontFace: "Calibri" } },
      { text: "None", options: { fill: { color: C.surface }, color: C.red, fontSize: 10, fontFace: "Calibri" } },
      { text: "Per-query token logging", options: { fill: { color: C.surface }, color: C.green, fontSize: 10, fontFace: "Calibri" } },
    ],
  ];

  slide.addTable(genRows, {
    x: 0.5, y: 1.65, w: 6.5,
    colW: [1.8, 2.0, 2.7],
    border: { pt: 0.5, color: "334155" },
    margin: [3, 5, 3, 5],
  });

  // ── Right table: vs Legacy Tools ──
  slide.addText("vs. Traditional Pharma Software", {
    x: 7.5, y: 1.15, w: 5.3, h: 0.45,
    fontSize: 20, fontFace: "Calibri", color: C.white,
    bold: true, align: "left", valign: "middle",
  });

  const legacyRows = [
    [
      { text: "Capability", options: { fill: { color: C.blue }, color: C.white, bold: true, fontSize: 10, fontFace: "Calibri" } },
      { text: "Legacy Tools", options: { fill: { color: C.blue }, color: C.white, bold: true, fontSize: 10, fontFace: "Calibri" } },
      { text: "PharmaAgent Pro", options: { fill: { color: C.blue }, color: C.white, bold: true, fontSize: 10, fontFace: "Calibri" } },
    ],
    [
      { text: "NL Queries", options: { fill: { color: C.surface }, color: C.light, fontSize: 10, fontFace: "Calibri" } },
      { text: "Structured forms", options: { fill: { color: C.surface }, color: C.red, fontSize: 10, fontFace: "Calibri" } },
      { text: "Natural language", options: { fill: { color: C.surface }, color: C.green, fontSize: 10, fontFace: "Calibri" } },
    ],
    [
      { text: "Cross-Domain", options: { fill: { color: "141E33" }, color: C.light, fontSize: 10, fontFace: "Calibri" } },
      { text: "Separate systems", options: { fill: { color: "141E33" }, color: C.red, fontSize: 10, fontFace: "Calibri" } },
      { text: "Unified platform", options: { fill: { color: "141E33" }, color: C.green, fontSize: 10, fontFace: "Calibri" } },
    ],
    [
      { text: "Setup Time", options: { fill: { color: C.surface }, color: C.light, fontSize: 10, fontFace: "Calibri" } },
      { text: "Months", options: { fill: { color: C.surface }, color: C.red, fontSize: 10, fontFace: "Calibri" } },
      { text: "Minutes", options: { fill: { color: C.surface }, color: C.green, fontSize: 10, fontFace: "Calibri" } },
    ],
    [
      { text: "Doc Generation", options: { fill: { color: "141E33" }, color: C.light, fontSize: 10, fontFace: "Calibri" } },
      { text: "Manual templates", options: { fill: { color: "141E33" }, color: C.red, fontSize: 10, fontFace: "Calibri" } },
      { text: "AI-generated, compliant", options: { fill: { color: "141E33" }, color: C.green, fontSize: 10, fontFace: "Calibri" } },
    ],
    [
      { text: "Learning Curve", options: { fill: { color: C.surface }, color: C.light, fontSize: 10, fontFace: "Calibri" } },
      { text: "Weeks of training", options: { fill: { color: C.surface }, color: C.red, fontSize: 10, fontFace: "Calibri" } },
      { text: "Conversational UI", options: { fill: { color: C.surface }, color: C.green, fontSize: 10, fontFace: "Calibri" } },
    ],
  ];

  slide.addTable(legacyRows, {
    x: 7.5, y: 1.65, w: 5.3,
    colW: [1.6, 1.8, 1.9],
    border: { pt: 0.5, color: "334155" },
    margin: [3, 5, 3, 5],
  });
})();

// ============================================================
// SLIDE 8: CASE STUDY
// ============================================================
(function () {
  const slide = pres.addSlide();
  slide.background = { color: C.bg };

  // Title
  slide.addText("Case Study: Safety Signal to Regulatory Report", {
    x: 0.5, y: 0.3, w: 12, h: 0.65,
    fontSize: 32, fontFace: "Arial Black", color: C.white,
    bold: true, align: "left", valign: "middle",
  });

  // Subtitle
  slide.addText("Oncolytin-B ILD Signal Detection \u2014 3 minutes vs. 3-5 days", {
    x: 0.5, y: 0.95, w: 12, h: 0.4,
    fontSize: 16, fontFace: "Arial", color: C.cyan,
    align: "left", valign: "middle",
  });

  // 3 step cards
  const steps = [
    {
      title: "Step 1: Signal Detection",
      titleColor: C.amber,
      borderColor: C.amber,
      time: "30 seconds",
      lines: [
        "Calls safety_signal_analysis tool",
        "Scans compound database",
        "3 Adverse Events detected",
        "2 Serious Adverse Events flagged",
        "ILD signal identified",
        "Status set to ALERT",
      ],
    },
    {
      title: "Step 2: Deep Dive",
      titleColor: C.blue,
      borderColor: C.blue,
      time: "45 seconds",
      lines: [
        "Calls adverse_event_search tool",
        "Retrieves detailed SAE records",
        "ILD: Grade 3 (Serious)",
        "QTc Prolongation: Grade 2",
        "Cross-references drug profile",
        "Identifies risk factors",
      ],
    },
    {
      title: "Step 3: Regulatory Report",
      titleColor: C.green,
      borderColor: C.green,
      time: "90 seconds",
      lines: [
        "Calls generate_document tool",
        "Produces ICH E2A CIOMS I form",
        "All required fields populated",
        "Compliance metadata validated",
        "Document ready for submission",
        "Audit trail logged",
      ],
    },
  ];

  const stepW = 3.8;
  const stepGap = 0.25;
  const totalStepW = steps.length * stepW + (steps.length - 1) * stepGap;
  const stepStartX = (SW - totalStepW) / 2;
  const stepY = 1.55;
  const stepH = 4.8;

  steps.forEach((s, i) => {
    const sx = stepStartX + i * (stepW + stepGap);

    slide.addShape(pres.shapes.RECTANGLE, {
      x: sx, y: stepY, w: stepW, h: stepH,
      fill: { color: C.surface },
      line: { color: s.borderColor, width: 2 },
    });

    // Title
    slide.addText(s.title, {
      x: sx + 0.2, y: stepY + 0.2, w: stepW - 0.4, h: 0.45,
      fontSize: 16, fontFace: "Calibri", color: s.titleColor,
      bold: true, align: "left", valign: "middle",
    });

    // Big time number
    slide.addText(s.time, {
      x: sx + 0.2, y: stepY + 0.75, w: stepW - 0.4, h: 0.6,
      fontSize: 24, fontFace: "Calibri", color: C.white,
      bold: true, align: "center", valign: "middle",
    });

    // Description lines
    const lineTexts = s.lines.map((l, li) => ({
      text: l,
      options: {
        bullet: true,
        breakLine: li < s.lines.length - 1,
        fontSize: 11,
        fontFace: "Calibri",
        color: C.light,
      },
    }));

    slide.addText(lineTexts, {
      x: sx + 0.2, y: stepY + 1.55, w: stepW - 0.4, h: stepH - 1.85,
      valign: "top",
    });
  });

  // Bottom callout
  slide.addText("Total: ~3 minutes  |  Traditional: 3-5 days", {
    x: 0.5, y: 6.6, w: SW - 1, h: 0.5,
    fontSize: 18, fontFace: "Calibri", color: C.green,
    bold: true, align: "center", valign: "middle",
  });
})();

// ============================================================
// SLIDE 9: FEATURE ROADMAP
// ============================================================
(function () {
  const slide = pres.addSlide();
  slide.background = { color: C.bg };

  // Title
  slide.addText("Feature Roadmap", {
    x: 0.5, y: 0.3, w: 10, h: 0.7,
    fontSize: 36, fontFace: "Arial Black", color: C.white,
    bold: true, align: "left", valign: "middle",
  });

  const phases = [
    {
      header: "NOW\nPhase 1: MVP",
      headerColor: C.green,
      borderColor: C.green,
      badge: "LIVE",
      badgeColor: C.green,
      items: [
        "6 pharma tools",
        "4 domain agents",
        "Guardrails & compliance",
        "Audit trail & tracking",
        "Managed Agent deploy",
        "Web + CLI chatbot",
      ],
    },
    {
      header: "Q3 2026\nPhase 2: Multi-Agent",
      headerColor: C.blue,
      borderColor: C.blue,
      badge: "PLANNED",
      badgeColor: C.dim,
      items: [
        "Parallel agent execution",
        "Agent-to-agent comms",
        "Supervisor agent",
        "Dynamic tool discovery",
        "Conflict resolution",
      ],
    },
    {
      header: "Q4 2026\nPhase 3: Enterprise",
      headerColor: C.cyan,
      borderColor: C.cyan,
      badge: "PLANNED",
      badgeColor: C.dim,
      items: [
        "RBAC & multi-tenant",
        "FDA FAERS API",
        "Document versioning",
        "Approval workflows",
        "Scheduled monitoring",
      ],
    },
    {
      header: "2027\nPhase 4: Advanced AI",
      headerColor: C.amber,
      borderColor: C.amber,
      badge: "FUTURE",
      badgeColor: C.dim,
      items: [
        "Literature RAG",
        "Predictive safety",
        "Auto IND/NDA assembly",
        "Multi-modal analysis",
        "Federated learning",
      ],
    },
  ];

  const phW = 2.85;
  const phGap = 0.25;
  const totalPhW = phases.length * phW + (phases.length - 1) * phGap;
  const phStartX = (SW - totalPhW) / 2;
  const phY = 1.3;
  const phH = 5.5;

  phases.forEach((ph, i) => {
    const px = phStartX + i * (phW + phGap);

    slide.addShape(pres.shapes.RECTANGLE, {
      x: px, y: phY, w: phW, h: phH,
      fill: { color: C.surface },
      line: { color: ph.borderColor, width: 2 },
    });

    // Phase header
    slide.addText(ph.header, {
      x: px + 0.15, y: phY + 0.15, w: phW - 0.3, h: 0.85,
      fontSize: 14, fontFace: "Calibri", color: ph.headerColor,
      bold: true, align: "center", valign: "top",
    });

    // Badge
    slide.addText(ph.badge, {
      x: px + 0.15, y: phY + 1.05, w: phW - 0.3, h: 0.35,
      fontSize: 10, fontFace: "Calibri", color: ph.badgeColor,
      bold: true, align: "center", valign: "middle",
    });

    // Bullet items
    const bulletTexts = ph.items.map((item, bi) => ({
      text: item,
      options: {
        bullet: true,
        breakLine: bi < ph.items.length - 1,
        fontSize: 11,
        fontFace: "Calibri",
        color: C.light,
      },
    }));

    slide.addText(bulletTexts, {
      x: px + 0.15, y: phY + 1.5, w: phW - 0.3, h: phH - 1.75,
      valign: "top",
    });
  });
})();

// ============================================================
// SLIDE 10: CLOSING
// ============================================================
(function () {
  const slide = pres.addSlide();
  slide.background = { color: C.bg };

  // Title
  slide.addText("PharmaAgent Pro", {
    x: 0.5, y: 0.8, w: SW - 1, h: 0.8,
    fontSize: 44, fontFace: "Arial Black", color: C.white,
    bold: true, align: "center", valign: "middle",
  });

  // Tagline
  slide.addText("From Compound to Clinic \u2014 Faster, Safer, Smarter", {
    x: 0.5, y: 1.7, w: SW - 1, h: 0.6,
    fontSize: 22, fontFace: "Arial", color: C.cyan,
    align: "center", valign: "middle",
  });

  // 3 value pillar cards
  const pillars = [
    { title: "FASTER", titleColor: C.green, body: "Signal detection in seconds, not weeks. Documents in minutes, not days." },
    { title: "SAFER", titleColor: C.blue, body: "Zero PII exposure. Full audit trail. FDA/ICH compliant by design." },
    { title: "SMARTER", titleColor: C.cyan, body: "AI reasons through complex drug interactions. Multi-agent specialization." },
  ];

  const pilW = 3.3;
  const pilGap = 0.35;
  const totalPilW = pillars.length * pilW + (pillars.length - 1) * pilGap;
  const pilStartX = (SW - totalPilW) / 2;
  const pilY = 2.8;
  const pilH = 2.5;

  pillars.forEach((p, i) => {
    const px = pilStartX + i * (pilW + pilGap);

    slide.addShape(pres.shapes.RECTANGLE, {
      x: px, y: pilY, w: pilW, h: pilH,
      fill: { color: C.surface },
      line: { color: p.titleColor, width: 2 },
    });

    slide.addText([
      { text: p.title, options: { fontSize: 22, fontFace: "Arial Black", color: p.titleColor, bold: true, breakLine: true } },
      { text: "", options: { fontSize: 10, breakLine: true } },
      { text: p.body, options: { fontSize: 13, fontFace: "Calibri", color: C.light } },
    ], {
      x: px + 0.2, y: pilY + 0.2, w: pilW - 0.4, h: pilH - 0.4,
      align: "center", valign: "middle",
    });
  });

  // Bottom tagline
  slide.addText("Built on Claude  |  Engineered for Pharma  |  Ready for Production", {
    x: 0.5, y: 6.2, w: SW - 1, h: 0.5,
    fontSize: 16, fontFace: "Calibri", color: C.dim,
    align: "center", valign: "middle",
  });
})();

// ── Write file ──
const outPath = path.join(__dirname, "PharmaAgent_Pro_Marketing_Deck.pptx");
pres.writeFile({ fileName: outPath })
  .then(() => {
    console.log("Created: " + outPath);
  })
  .catch((err) => {
    console.error("Error:", err);
    process.exit(1);
  });
