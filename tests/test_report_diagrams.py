"""Viability chart in both languages."""

from __future__ import annotations

from src import report_diagrams as rd


def test_viability_chart_renders_in_portuguese_and_english(tmp_path) -> None:
    pt, en = tmp_path / "pt.png", tmp_path / "en.png"
    rd.viability_figure(pt)
    rd.viability_figure(en, lang="en")
    assert pt.stat().st_size > 20_000 and en.stat().st_size > 20_000


def test_both_languages_have_the_same_labels() -> None:
    assert rd.VIABILITY_TEXT["pt"].keys() == rd.VIABILITY_TEXT["en"].keys()
