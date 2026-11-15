"""Draw the project logo as two transparent SVG files (light and dark themes).

The README shows one or the other through a ``<picture>`` element, so the logo needs no white background and
reads on both GitHub themes. The card is a carbon-fibre weave with hexagonal wrench cutouts, an orange chamfer
line and a ruler scale. It avoids SVG patterns, masks, clip paths and gradients (the holes are sub-paths of the outline, the
weave is a set of squares that fit on the card) so every renderer draws it the same way.

    python scripts/make_logo.py
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRAND = ROOT / "assets" / "brand"

X, Y, W, H, R = 20, 38, 240, 152, 16
TILE = 7

THEMES = {
    "light": {"base": "#1c2126", "tile": "#2a3138", "edge": None, "accent": "#ef6c00",
              "title": "#1c2126", "tagline": "#57606a"},
    "dark": {"base": "#323a42", "tile": "#434d56", "edge": "#8b98a5", "accent": "#ff8f3a",
             "title": "#f0f3f6", "tagline": "#9aa7b4"},
}


def rounded_rectangle() -> str:
    return (f"M{X + R},{Y} H{X + W - R} A{R},{R} 0 0 1 {X + W},{Y + R} V{Y + H - R} A{R},{R} 0 0 1 {X + W - R},{Y + H} "
            f"H{X + R} A{R},{R} 0 0 1 {X},{Y + H - R} V{Y + R} A{R},{R} 0 0 1 {X + R},{Y} Z")


def hexagon(cx: float, cy: float, r: float) -> str:
    h = 0.866 * r
    points = [(cx + r, cy), (cx + r / 2, cy + h), (cx - r / 2, cy + h), (cx - r, cy), (cx - r / 2, cy - h), (cx + r / 2, cy - h)]
    return "M" + " L".join(f"{px:.1f},{py:.1f}" for px, py in points) + " Z"


def card_path() -> str:
    """Outline plus three hexagonal holes; with the even-odd rule the hexagons are cut out of the card."""
    return " ".join([rounded_rectangle(), *[hexagon(cx, cy, r) for cx, cy, r in HOLES]])


HOLES = ((56, 66, 20), (54, 114, 17), (52, 152, 14))


def inside_card(px: float, py: float) -> bool:
    """Point test for the rounded rectangle."""
    if not (X <= px <= X + W and Y <= py <= Y + H):
        return False
    cx = min(max(px, X + R), X + W - R)
    cy = min(max(py, Y + R), Y + H - R)
    return (px - cx) ** 2 + (py - cy) ** 2 <= R * R


def inside_hole(px: float, py: float) -> bool:
    """Point test for the hexagons (circle of the circumscribed radius, a little generous)."""
    return any((px - cx) ** 2 + (py - cy) ** 2 <= (r + 1.5) ** 2 for cx, cy, r in HOLES)


def weave() -> str:
    """Light squares of the weave that lie entirely on the card and clear of the holes."""
    squares = []
    for row in range(H // TILE + 1):
        for col in range(W // TILE + 1):
            if (row + col) % 2:
                continue
            x, y = X + col * TILE, Y + row * TILE
            corners = [(x, y), (x + TILE, y), (x, y + TILE), (x + TILE, y + TILE)]
            if all(inside_card(px, py) and not inside_hole(px, py) for px, py in corners):
                squares.append(f'<rect x="{x}" y="{y}" width="{TILE}" height="{TILE}"/>')
    return "".join(squares)


def logo(theme: str) -> str:
    c = THEMES[theme]
    ticks = "".join(
        f'<line x1="{x}" y1="174" x2="{x}" y2="{164 if k % 2 == 0 else 168}"/>' for k, x in enumerate(range(110, 231, 20)))
    edge = (f'<path d="{card_path()}" fill="none" stroke="{c["edge"]}" stroke-opacity="0.55" stroke-width="1.5" '
            f'fill-rule="evenodd"/>') if c["edge"] else ""
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 230" width="800" height="230" role="img" aria-labelledby="t d">
  <title id="t">Carbon Fiber EDC Multitool</title>
  <desc id="d">A carbon-fibre card with hexagonal wrench cutouts, a chamfer line and a ruler scale, next to the project name.</desc>
  <path d="{card_path()}" fill="{c['base']}" fill-rule="evenodd"/>
  <g fill="{c['tile']}">{weave()}</g>
  {edge}
  <line x1="98" y1="62" x2="238" y2="62" stroke="{c['accent']}" stroke-width="3.5" stroke-linecap="round"/>
  <g stroke="{c['accent']}" stroke-width="2.5" stroke-linecap="round">{ticks}</g>
  <g font-family="'Segoe UI', 'Helvetica Neue', Arial, sans-serif">
    <text x="296" y="106" font-size="58" font-weight="700" fill="{c['title']}" letter-spacing="-1">Carbon Fiber</text>
    <text x="296" y="164" font-size="58" font-weight="300" fill="{c['title']}" letter-spacing="-1"><tspan fill="{c['accent']}" font-weight="700">EDC</tspan> Multitool</text>
    <text x="298" y="199" font-size="17" font-weight="600" fill="{c['tagline']}" letter-spacing="3.2">EVIDENCE-LED PRODUCT DEVELOPMENT</text>
  </g>
</svg>
"""


def main() -> None:
    BRAND.mkdir(parents=True, exist_ok=True)
    for theme in THEMES:
        target = BRAND / f"logo-{theme}.svg"
        target.write_text(logo(theme), encoding="utf-8")
        print("wrote", target)


if __name__ == "__main__":
    main()
