"""Render LinkedIn blog opening image for PharmaAgent Pro."""
from __future__ import annotations

import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = Path(__file__).parent / "diagrams" / "linkedin_cover.png"
OUT.parent.mkdir(exist_ok=True)

# LinkedIn blog header sweet spot
W, H = 1200, 627

# Generous horizontal margins — content lives in the center column
MARGIN_X = 180
CENTER_W = W - 2 * MARGIN_X  # 840px

# Palette — deep navy/teal with cyan + mint accents (tech + clinical)
BG_TOP = (8, 14, 32)
BG_BOTTOM = (16, 34, 58)
ACCENT_CYAN = (82, 196, 232)
ACCENT_MINT = (110, 231, 183)
ACCENT_VIOLET = (167, 139, 250)
INK = (240, 246, 255)
DIM = (170, 190, 215)

FONT_REG = "/System/Library/Fonts/Supplemental/Helvetica.ttc"
FONT_BOLD = "/System/Library/Fonts/Helvetica.ttc"
FONT_MONO = "/System/Library/Fonts/Menlo.ttc"


def gradient_bg(img: Image.Image) -> None:
    """Vertical gradient + subtle radial highlight behind the center."""
    w, h = img.size
    px = img.load()
    for y in range(h):
        t = y / (h - 1)
        r = int(BG_TOP[0] * (1 - t) + BG_BOTTOM[0] * t)
        g = int(BG_TOP[1] * (1 - t) + BG_BOTTOM[1] * t)
        b = int(BG_TOP[2] * (1 - t) + BG_BOTTOM[2] * t)
        for x in range(w):
            px[x, y] = (r, g, b)

    # Soft radial glow behind the title
    glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(glow)
    cx, cy = w // 2, int(h * 0.45)
    for radius, alpha in [(420, 28), (300, 38), (180, 46)]:
        gdraw.ellipse(
            (cx - radius, cy - radius, cx + radius, cy + radius),
            fill=(ACCENT_CYAN[0], ACCENT_CYAN[1], ACCENT_CYAN[2], alpha),
        )
    glow = glow.filter(ImageFilter.GaussianBlur(70))
    img.alpha_composite(glow) if img.mode == "RGBA" else img.paste(
        Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB")
    )


def draw_molecule_network(img: Image.Image) -> None:
    """Decorative molecule/agent-graph nodes in the side margins — subtle."""
    draw = ImageDraw.Draw(img, "RGBA")
    rng = random.Random(7)

    def field(x0: int, x1: int, n: int) -> list[tuple[int, int]]:
        pts = []
        for _ in range(n):
            pts.append((rng.randint(x0, x1), rng.randint(40, H - 40)))
        return pts

    left = field(20, MARGIN_X - 30, 14)
    right = field(W - MARGIN_X + 30, W - 20, 14)

    for cluster in (left, right):
        # edges — connect nearby points
        for i, a in enumerate(cluster):
            for b in cluster[i + 1:]:
                d = math.hypot(a[0] - b[0], a[1] - b[1])
                if d < 130:
                    alpha = max(10, int(70 - d * 0.35))
                    draw.line([a, b], fill=(ACCENT_CYAN[0], ACCENT_CYAN[1], ACCENT_CYAN[2], alpha), width=1)
        # nodes
        for (x, y) in cluster:
            r = rng.choice([2, 3, 3, 4])
            color = rng.choice([ACCENT_CYAN, ACCENT_MINT, ACCENT_VIOLET])
            draw.ellipse((x - r, y - r, x + r, y + r),
                         fill=(color[0], color[1], color[2], 210))


def draw_hex(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int,
             outline: tuple, width: int = 2, fill=None) -> None:
    pts = [
        (cx + r * math.cos(math.radians(60 * i - 30)),
         cy + r * math.sin(math.radians(60 * i - 30)))
        for i in range(6)
    ]
    if fill:
        draw.polygon(pts, fill=fill)
    draw.polygon(pts, outline=outline, width=width)


def draw_center_emblem(img: Image.Image) -> None:
    """A hex lattice (molecule) with a pulse ring — the visual anchor."""
    d = ImageDraw.Draw(img, "RGBA")
    cx, cy = W // 2, 190

    # outer pulse rings
    for r, a in [(90, 50), (70, 80), (52, 120)]:
        d.ellipse((cx - r, cy - r, cx + r, cy + r),
                  outline=(ACCENT_CYAN[0], ACCENT_CYAN[1], ACCENT_CYAN[2], a),
                  width=2)

    # hex lattice — 1 center + 6 around (benzene-ring-ish motif)
    R = 30
    positions = [(cx, cy)]
    for i in range(6):
        angle = math.radians(60 * i)
        positions.append((
            int(cx + R * 1.732 * math.cos(angle)),
            int(cy + R * 1.732 * math.sin(angle)),
        ))

    for (x, y) in positions:
        draw_hex(d, x, y, R, outline=(*ACCENT_MINT, 230), width=2,
                 fill=(*ACCENT_MINT, 22))

    # center filled brighter
    draw_hex(d, cx, cy, R, outline=(*ACCENT_CYAN, 255), width=3,
             fill=(*ACCENT_CYAN, 60))


def load_font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size)


def centered_text(draw: ImageDraw.ImageDraw, y: int, text: str,
                  font: ImageFont.FreeTypeFont, fill, tracking: int = 0) -> int:
    if tracking == 0:
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        draw.text(((W - tw) // 2, y), text, font=font, fill=fill)
        return bbox[3] - bbox[1]
    # manual tracking for kerned caps
    widths = [draw.textbbox((0, 0), ch, font=font)[2] for ch in text]
    total = sum(widths) + tracking * (len(text) - 1)
    x = (W - total) // 2
    for ch, w in zip(text, widths):
        draw.text((x, y), ch, font=font, fill=fill)
        x += w + tracking
    bbox = draw.textbbox((0, 0), "Mg", font=font)
    return bbox[3] - bbox[1]


def pill(draw: ImageDraw.ImageDraw, cx: int, y: int, label: str,
         font: ImageFont.FreeTypeFont, color: tuple) -> int:
    pad_x, pad_y = 14, 7
    bbox = draw.textbbox((0, 0), label, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    w = tw + pad_x * 2
    h = th + pad_y * 2
    x0 = cx - w // 2
    y0 = y
    draw.rounded_rectangle((x0, y0, x0 + w, y0 + h), radius=h // 2,
                           fill=(color[0], color[1], color[2], 40),
                           outline=(color[0], color[1], color[2], 220), width=2)
    draw.text((x0 + pad_x, y0 + pad_y - 2), label, font=font, fill=INK)
    return w


def draw_pill_row(draw: ImageDraw.ImageDraw, y: int,
                  items: list[tuple[str, tuple]],
                  font: ImageFont.FreeTypeFont, gap: int = 16) -> None:
    # measure
    widths = []
    for label, _ in items:
        bbox = draw.textbbox((0, 0), label, font=font)
        widths.append(bbox[2] - bbox[0] + 28)  # padding
    total = sum(widths) + gap * (len(items) - 1)
    x = (W - total) // 2
    for (label, color), w in zip(items, widths):
        pill(draw, x + w // 2, y, label, font, color)
        x += w + gap


def main() -> None:
    img = Image.new("RGB", (W, H), BG_TOP)
    gradient_bg(img)
    img = img.convert("RGBA")

    draw_molecule_network(img)
    draw_center_emblem(img)

    draw = ImageDraw.Draw(img, "RGBA")

    # tiny eyebrow label
    eyebrow_font = load_font(FONT_MONO, 15)
    centered_text(draw, 300, "C L A U D E   ×   P H A R M A",
                  eyebrow_font, ACCENT_CYAN, tracking=4)

    # Title — two lines, tight leading
    title_font = load_font(FONT_BOLD, 58)
    centered_text(draw, 330, "Managed Agents, Molecules,", title_font, INK)
    centered_text(draw, 395, "and the Future of Pharma", title_font, INK)

    # Subtitle
    sub_font = load_font(FONT_REG, 22)
    centered_text(draw, 478,
                  "Building, deploying, and scaling Claude agents",
                  sub_font, DIM)
    centered_text(draw, 508,
                  "for drug discovery, trials, regulatory, and safety.",
                  sub_font, DIM)

    # Pills row
    pill_font = load_font(FONT_MONO, 14)
    draw_pill_row(draw, 558, [
        ("Claude Opus 4.6", ACCENT_CYAN),
        ("Managed Agents", ACCENT_MINT),
        ("Pharma Intelligence", ACCENT_VIOLET),
    ], pill_font, gap=14)

    # Thin accent rule under the emblem
    d2 = ImageDraw.Draw(img, "RGBA")
    d2.line([(W // 2 - 60, 280), (W // 2 + 60, 280)],
            fill=(*ACCENT_CYAN, 180), width=2)

    # Faint margin guides — remove; but keep content fenced visually with
    # subtle vertical accent bars at the margins
    bar_alpha = 90
    d2.line([(MARGIN_X - 40, 120), (MARGIN_X - 40, H - 120)],
            fill=(*ACCENT_CYAN, bar_alpha), width=1)
    d2.line([(W - MARGIN_X + 40, 120), (W - MARGIN_X + 40, H - 120)],
            fill=(*ACCENT_CYAN, bar_alpha), width=1)

    img.convert("RGB").save(OUT, "PNG", optimize=True)
    print(f"wrote {OUT}  ({W}x{H})")


if __name__ == "__main__":
    main()
