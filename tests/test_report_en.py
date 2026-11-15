"""The English edition of the report: structure, language, citations, numbers and the published PDF."""

from __future__ import annotations

import math
import re
import shutil
from pathlib import Path

import pytest
from docx.oxml.ns import qn

from src import docx_builder, report_diagrams, strategic_analysis
from src import generate_report_en as en
from src import project_plan as pp
from src import reverse_logistics_model as rl

ROOT = Path(__file__).resolve().parents[1]
MATH = "{http://schemas.openxmlformats.org/officeDocument/2006/math}"


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    """Build the edition with figures drawn into a temporary folder (tracked PNG files stay untouched)."""
    figures = tmp_path_factory.mktemp("figures_en")
    shutil.copytree(ROOT / "outputs" / "visualizations", figures, dirs_exist_ok=True)
    report_diagrams.render_all(figures)
    strategic_analysis.FIG_DIR = figures
    strategic_analysis.render_all()
    original = docx_builder.FIGURES
    docx_builder.FIGURES = figures
    try:
        yield en.build_report()
    finally:
        docx_builder.FIGURES = original
        strategic_analysis.FIG_DIR = ROOT / "outputs" / "visualizations"


def texts(builder) -> list[str]:
    """Paragraph and cell texts, with the non-breaking space and hyphen the table fitter adds turned back."""
    raw = ["".join(t.text or "" for t in el.iter(qn("w:t"))) for el in builder.doc.element.body.iter(qn("w:p"))]
    return [text.replace(" ", " ").replace("‑", "-") for text in raw]


def test_structure(built) -> None:
    text = "\n".join(texts(built))
    for heading in ("1. Product and market", "2. Concept design", "3. Project plan", "4. Economic viability",
                    "5. End of life", "6. Conclusion and open points", "References"):
        assert heading in text, heading


def test_report_is_english_and_free_of_dashes(built) -> None:
    text = "\n".join(texts(built))
    for portuguese in ("Tabela", "Figura", "Seção", "Fonte:", "Apêndice", "Referências"):
        assert portuguese not in text, portuguese
    assert "—" not in text and "–" not in text
    assert not re.search(r"(Table|Figure|Section) \?", text), "unresolved cross-reference"
    expected = {label for group in en.LABEL_MAP.values() for label in group.values()}
    assert expected <= set(built.labels), expected - set(built.labels)


def test_citations_are_contiguous_cited_and_listed(built) -> None:
    paragraphs = texts(built)
    start = next(i for i, t in enumerate(paragraphs) if t.strip() == "References")
    listed = [int(m.group(1)) for t in paragraphs[start:] for m in [re.match(r"\[(\d+)\]", t)] if m]
    assert listed == list(range(1, len(listed) + 1))
    body = "\n".join(paragraphs[:start])
    cited = {int(n) for n in re.findall(r"\[(\d+)(?=[\],])", body)}
    assert cited == set(listed), (cited ^ set(listed))
    first_use = [int(m) for m in re.findall(r"\[(\d+)\]", body)]
    assert first_use[0] == 1  # numbered in the order of first citation


def test_numbers_come_from_the_model_and_agree_with_the_portuguese_edition(built) -> None:
    p = rl.load_assumptions()
    unit_net = p["net_price_brl"] - p["variable_cost_brl"] - rl.end_of_life_unit_cost(p)
    text = "\n".join(texts(built))
    assert f"{math.ceil(pp.BUDGET / unit_net)} cards" in text
    assert f"positive from {math.ceil(pp.units_for_zero_npv(unit_net))}" in text
    for units in (600, 1000, 2000):
        e = pp.economics(units, unit_net)
        assert f"R$ {e['npv']:,.0f}" in text and f"{e['payback_months']:,.1f}" in text
    assert f"R$ {pp.BUDGET:,.0f} plus a R$ {pp.RESERVE:,.0f} reserve" in text
    assert "A1 → A2 → A3 → A5 → A6 → A7 → A8 → A9" in text


def test_equations_are_the_shared_model(built) -> None:
    assert len(list(built.doc.element.body.iter(MATH + "oMathPara"))) == 7
    math_text = "".join(t.text or "" for t in built.doc.element.body.iter(MATH + "t"))
    assert "NPV" in math_text and "IRR" in math_text and "VPL" not in math_text and "para" not in math_text


def test_figures_are_not_shrunk_below_a_readable_scale(built) -> None:
    too_small = [(name, round(scale, 2)) for name, _, scale in built.figure_log if scale < 0.5]
    assert not too_small, too_small


def test_published_pdf_matches_the_code(built) -> None:
    """The PDF in docs/report is committed. If the text of the edition changed, regenerate it with
    ``scripts/build_report_pdf.ps1 -Edition en``, which also refreshes the hash that this test compares."""
    pdf = en.PDF_DIR / en.PDF_NAME
    assert pdf.exists() and pdf.stat().st_size > 100_000 and pdf.read_bytes()[:5] == b"%PDF-"
    expected = en.HASH_FILE.read_text(encoding="utf-8").strip()
    assert en.report_text_hash(built.doc) == expected, "the English edition changed: rebuild and commit the PDF"


def test_readme_links_to_the_published_report() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    link = f"docs/report/{en.PDF_NAME}"
    assert link in readme and (ROOT / link).exists()
