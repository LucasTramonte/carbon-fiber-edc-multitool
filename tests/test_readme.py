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
