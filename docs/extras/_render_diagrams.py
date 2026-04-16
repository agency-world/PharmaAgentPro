"""Render the two ASCII process diagrams to PNG."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT_DIR = Path(__file__).parent / "diagrams"
OUT_DIR.mkdir(exist_ok=True)

FONT_PATH = "/System/Library/Fonts/Menlo.ttc"
FONT_SIZE = 16
PADDING = 32
BG = (18, 20, 28)
FG = (230, 233, 240)
ACCENT = (120, 170, 255)

DIAGRAM_1 = r"""
┌─────────────────────────────────────────────────────────────────────┐
│  USER                                                               │
│  "Run safety signal analysis on Oncolytin-B"                        │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
        ┌──────────────────────────────────────────────┐
        │  GUARDRAILS — PRE-FLIGHT                     │
        ├──────────────────────────────────────────────┤
        │  ✓ Rate Limiter ........ PASS (23 remaining) │
        │  ✓ Input Validator ..... PII: none           │
        │                          Injection: clean    │
        └──────────────────────────────┬───────────────┘
                                       │
                                       ▼
        ┌──────────────────────────────────────────────┐
        │  ORCHESTRATOR                                │
        │  ─────────────                               │
        │   │                                          │
        │   └──► Haiku 4.5 Classifier                  │
        │         {                                    │
        │           "domain":     "safety",            │
        │           "confidence": 0.95                 │
        │         }                                    │
        │                                              │
        │   Route ► Safety Agent (Opus 4.6 + Thinking) │
        └──────────────────────────────┬───────────────┘
                                       │
                                       ▼
        ┌──────────────────────────────────────────────┐
        │  SAFETY AGENT  (Opus 4.6, extended thinking) │
        ├──────────────────────────────────────────────┤
        │                                              │
        │   API Call #1 ─────────────────────────────► │
        │     tool: safety_signal_analysis             │
        │     args: { drug: "Oncolytin-B" }            │
        │     ◄── ALERT: ILD signal, 2 SAEs            │
        │                                              │
        │   API Call #2 ─────────────────────────────► │
        │     tool: adverse_event_search               │
        │     args: { serious_only: true }             │
        │     ◄── 2 SAE records with narratives        │
        │                                              │
        │   API Call #3 ─────────────────────────────► │
        │     synthesize final response (end_turn)     │
        │                                              │
        └──────────────────────────────┬───────────────┘
                                       │
                                       ▼
        ┌──────────────────────────────────────────────┐
        │  GUARDRAILS — POST-FLIGHT                    │
        ├──────────────────────────────────────────────┤
        │  ✓ Output Filter ....... 0 redactions        │
        │                          compliance footer ✓ │
        └──────────────────────────────┬───────────────┘
                                       │
                                       ▼
        ┌──────────────────────────────────────────────┐
        │  OBSERVABILITY                               │
        ├──────────────────────────────────────────────┤
        │  Audit Logger .......... query               │
        │                          + 2 tool_use        │
        │                          + response          │
        │  Usage Tracker ......... ~5,000 input tokens │
        │                          ~$0.19              │
        └──────────────────────────────┬───────────────┘
                                       │
                                       ▼
                            ┌──────────────────┐
                            │  RESPONSE → USER │
                            └──────────────────┘
""".strip("\n")

DIAGRAM_2 = r"""
┌──────────────────────────┐                    ┌──────────────────────────┐
│        CLIENT            │                    │   CLAUDE MANAGED AGENT   │
│  (chatbot.py / browser)  │                    │   PLATFORM (SSE stream)  │
└────────────┬─────────────┘                    └─────────────┬────────────┘
             │                                                │
             │                                                │
             │  ──── user.message ───────────────────────►    │
             │       "Look up compound Oncolytin-B"           │
             │                                                │
             │                                       ┌────────┴────────┐
             │                                       │ Agent processes │
             │                                       │  (Opus 4.6)     │
             │                                       └────────┬────────┘
             │                                                │
             │  ◄──── agent.custom_tool_use ─────────────     │
             │         tool: drug_lookup                      │
             │         id:   evt_abc                          │
             │         args: { name: "Oncolytin-B" }          │
             │                                                │
             │  ◄──── session.status_idle ───────────────     │
             │         status: requires_action                │
             │                                                │
   ┌─────────┴─────────┐                                      │
   │ Execute tool      │                                      │
   │ locally           │                                      │
   │ (src/tools/…)     │                                      │
   └─────────┬─────────┘                                      │
             │                                                │
             │  ──── user.custom_tool_result ────────────►    │
             │        custom_tool_use_id: "evt_abc"           │
             │        result: { compound: {...} }             │
             │                                                │
             │                                       ┌────────┴────────┐
             │                                       │ Agent resumes   │
             │                                       │ reasoning       │
             │                                       └────────┬────────┘
             │                                                │
             │  ◄──── agent.message ─────────────────────     │
             │         "Oncolytin-B is a tyrosine             │
             │          kinase inhibitor…"                    │
             │         (final response)                       │
             │                                                │
             │  ◄──── session.status_idle ───────────────     │
             │         status: end_turn                       │
             │                                                │
             ▼                                                ▼

 ╔══════════════════════════════════════════════════════════════════╗
 ║  LEGEND                                                          ║
 ║  ──►  client → platform event                                    ║
 ║  ◄──  platform → client event (SSE)                              ║
 ║  evt_abc  correlates tool_use <-> tool_result                    ║
 ╚══════════════════════════════════════════════════════════════════╝
""".strip("\n")


def render(text: str, out_path: Path, title: str) -> None:
    font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
    title_font = ImageFont.truetype(FONT_PATH, FONT_SIZE + 4)

    lines = text.splitlines()

    # Measure
    bbox = font.getbbox("M")
    char_w = bbox[2] - bbox[0]
    line_h = (bbox[3] - bbox[1]) + 6

    max_chars = max(len(line) for line in lines)
    width = max_chars * char_w + PADDING * 2
    # add space for title
    title_block = line_h + 16
    height = len(lines) * line_h + PADDING * 2 + title_block

    img = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(img)

    draw.text((PADDING, PADDING), title, font=title_font, fill=ACCENT)

    y = PADDING + title_block
    for line in lines:
        draw.text((PADDING, y), line, font=font, fill=FG)
        y += line_h

    img.save(out_path, "PNG")
    print(f"wrote {out_path}  ({width}x{height})")


if __name__ == "__main__":
    render(DIAGRAM_1, OUT_DIR / "01_request_pipeline.png",
           "PharmaAgent Pro  —  Request Pipeline")
    render(DIAGRAM_2, OUT_DIR / "02_managed_agent_sse_flow.png",
           "Claude Managed Agent  —  Custom Tool SSE Flow")
