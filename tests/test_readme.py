"""The README renders on GitHub and its numbers come from the model."""

from __future__ import annotations

import re
from pathlib import Path

from src import project_plan as pp
from src import reverse_logistics_model as rl

README = (Path(__file__).resolve().parents[1] / "README.md").read_text(encoding="utf-8")


def _outside_code_fences(text: str) -> list[str]:
    """Lines of the README that are not inside a fenced block (math fences are checked separately)."""
    lines, fenced = [], False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        if not fenced:
            lines.append(line)
    return lines


def _math_fences(text: str) -> list[str]:
    blocks, current, inside = [], [], False
    for line in text.splitlines():
        if line.strip() == "```math":
            inside, current = True, []
        elif inside and line.strip() == "```":
            blocks.append("\n".join(current))
            inside = False
        elif inside:
            current.append(line)
    return blocks


def test_viability_table_matches_the_model() -> None:
    p = rl.load_assumptions()
    unit_net = p["net_price_brl"] - p["variable_cost_brl"] - rl.end_of_life_unit_cost(p)
    for units in (600, 1000, 2000):
        e = pp.economics(units, unit_net)
        row = (f"| {units:,} | {e['payback_months']:.1f} | {e['roi'] * 100:.0f}% | {e['npv']:,.0f} | "
               f"{e['irr_monthly'] * 100:.1f}% |")
        assert row in README, row
    assert f"needs {int(pp.BUDGET / unit_net) + 1} cards" in README
    assert f"positive from {round(pp.units_for_zero_npv(unit_net))}" in README
    assert f"$`c_f = {rl.end_of_life_unit_cost(p):.2f}`$" in README


def test_equations_are_in_math_fences_not_in_dollar_blocks() -> None:
    """GitHub runs Markdown before the math in ``$$`` blocks: ``*`` becomes italics, ``\\{`` loses its backslash
    and ``%`` starts a LaTeX comment. Fenced ``math`` blocks and ``$`...`$`` are not touched by Markdown."""
    assert "$$" not in README
    assert len(_math_fences(README)) >= 7
    for block in _math_fences(README):
        assert "*" not in block and "%" not in block, block
        assert block.count("{") == block.count("}"), block
        assert block.count("\\left") == block.count("\\right"), block


def test_inline_dollars_only_wrap_math_in_backticks() -> None:
    """Every ``$`` outside code must open or close ``$`...`$``; amounts are written in BRL, never ``R$``."""
    for line in _outside_code_fences(README):
        remaining = re.sub(r"\$`[^`]+`\$", "", line)
        assert "$" not in remaining, line
    for inline in re.findall(r"\$`([^`]+)`\$", README):
        assert "*" not in inline and "%" not in inline, inline
        assert inline.count("{") == inline.count("}"), inline


def test_at_a_glance_numbers_match_the_models() -> None:
    from src import generate_report_docx as gr
    from src import strategic_analysis as sa

    p = rl.load_assumptions()
    unit_net = p["net_price_brl"] - p["variable_cost_brl"] - rl.end_of_life_unit_cost(p)
    scores = gr.concept_scores()
    t_be = pp.payback_months(pp.cash_flows(1000, unit_net))
    glance = README.split("## At a glance")[1].split("## Contents")[0]
    expected = (
        f"weighted score {scores['B']:.2f} against {scores['A']:.2f} and {scores['C']:.2f}",
        f"BRL {pp.BUDGET:,.0f} plus a BRL {pp.RESERVE:,.0f} reserve",
        f"critical path {', '.join(pp.critical_path())}",
        f"Break-even at {int(pp.BUDGET / unit_net) + 1} cards (month {t_be:.1f}",
        f"NPV positive from {round(pp.units_for_zero_npv(unit_net))} cards at the {pp.DISCOUNT_RATE * 100:.2f}% Selic",
        f"pressure {sa.porter_mean():.1f} out of 5",
    )
    for fragment in expected:
        assert fragment in glance, fragment


def _slug(heading: str) -> str:
    """GitHub's anchor for a heading: lower case, punctuation removed, spaces turned into hyphens."""
    text = re.sub(r"[^\w\- ]", "", heading.strip().lower())
    return text.replace(" ", "-")


def test_relative_links_and_images_point_to_files_that_exist() -> None:
    root = Path(__file__).resolve().parents[1]
    targets = re.findall(r"\]\(([^)\s]+)\)", README) + re.findall(r'(?:src|srcset|href)="([^"]+)"', README)
    checked = 0
    for target in targets:
        if target.startswith(("http://", "https://", "#", "mailto:")):
            continue
        path = target.split("#")[0]
        assert (root / path).exists(), f"README points to a missing file: {target}"
        checked += 1
    assert checked >= 8  # logo (two), report, license, citation, data README, outputs README, chart


def test_in_page_links_match_a_heading() -> None:
    headings = {_slug(m.group(1)) for line in _outside_code_fences(README)
                for m in [re.match(r"#{1,6}\s+(.*)", line)] if m}
    anchors = re.findall(r"\]\(#([^)\s]+)\)", README)
    assert anchors
    missing = [a for a in anchors if a not in headings]
    assert not missing, missing


def test_logo_files_are_transparent_vector_drawings() -> None:
    brand = Path(__file__).resolve().parents[1] / "assets" / "brand"
    for name in ("logo-light.svg", "logo-dark.svg"):
        svg = (brand / name).read_text(encoding="utf-8")
        assert svg.lstrip().startswith("<svg") and "<title" in svg
        assert "<image" not in svg and "background" not in svg.lower()
        for fragile in ("<pattern", "<mask", "<clipPath", "Gradient"):
            assert fragile not in svg, f"{name} uses {fragile}, which some renderers ignore"
    assert not (brand / "product-mark.png").exists(), "the old raster logo (watermarked stock image) is gone"
