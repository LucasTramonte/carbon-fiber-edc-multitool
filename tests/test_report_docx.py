"""Tests for the generated Portuguese report (structure, numbering, language, citations)."""

import re
from pathlib import Path

import pytest
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml.ns import qn

from src import generate_report_docx as gr
from src import report_diagrams, reverse_flow_diagram, strategic_analysis
from src import reverse_logistics_model as rl

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def doc():
    rl.run()
    reverse_flow_diagram.write_all(png_dir=ROOT / "outputs" / "visualizations")
    report_diagrams.render_all()
    strategic_analysis.render_all()
    return gr.build_report().doc


def _texts(document) -> list[str]:
    """All paragraph and table-cell text, in document order."""
    out = []
    for el in document.element.body.iter(qn("w:p")):
        out.append("".join(t.text or "" for t in el.iter(qn("w:t"))))
    return out


def test_required_sections_and_appendices_exist(doc) -> None:
    text = "\n".join(_texts(doc))
    for heading in (
        "1. Planejamento estratégico do produto", "1.5 Análise do ambiente: SWOT e cinco forças de Porter",
        "2.6 Viabilidade econômica", "2. Planejamento do projeto", "3. Projeto conceitual",
        "4. Projeto detalhado", "5. Lançamento do produto", "6. Descontinuidade do produto",
        "7. Conclusão", "Referências",
        "Apêndice A", "Apêndice B",
    ):
        assert heading in text, heading


def test_figure_and_table_numbers_are_sequential(doc) -> None:
    paragraphs = _texts(doc)
    body_figs = [int(m.group(1)) for t in paragraphs for m in [re.match(r"Figura (\d+):", t)] if m]
    body_tabs = [int(m.group(1)) for t in paragraphs for m in [re.match(r"Tabela (\d+):", t)] if m]
    assert body_figs == list(range(1, len(body_figs) + 1)) and len(body_figs) >= 8
    assert body_tabs == list(range(1, len(body_tabs) + 1)) and len(body_tabs) >= 19
    for letter in "AB":
        figs = [int(m.group(1)) for t in paragraphs for m in [re.match(rf"Figura {letter}\.(\d+):", t)] if m]
        assert figs == list(range(1, len(figs) + 1))
    # in-text mentions must point to captions that exist
    text = "\n".join(t for t in paragraphs if not t.startswith(("Figura", "Tabela")))
    for n in map(int, re.findall(r"(?<![A-B]\.)\bTabela (\d+)\b", text)):
        assert n <= len(body_tabs), f"Tabela {n} mentioned but only {len(body_tabs)} exist"
    for n in map(int, re.findall(r"(?<![A-B]\.)\bFigura (\d+)\b", text)):
        assert n <= len(body_figs), f"Figura {n} mentioned but only {len(body_figs)} exist"


def test_citations_are_contiguous_cited_and_listed(doc) -> None:
    paragraphs = _texts(doc)
    start = next(i for i, t in enumerate(paragraphs) if t.strip() == "Referências")
    end = next(i for i, t in enumerate(paragraphs) if t.startswith("Apêndice A"))
    listed = [int(m.group(1)) for t in paragraphs[start:end] for m in [re.match(r"\[(\d+)\]", t)] if m]
    assert listed == list(range(1, len(listed) + 1))
    rest = "\n".join(paragraphs[:start] + paragraphs[end:])
    cited = {int(n) for n in re.findall(r"\[(\d+)(?=[\],])", rest)}
    assert cited <= set(listed), cited - set(listed)
    assert set(listed) <= cited, f"listed but never cited: {set(listed) - cited}"


def test_report_is_in_portuguese_and_in_scope(doc) -> None:
    text = "\n".join(_texts(doc))
    for banned in ("benchmark", "takeaway", "baseline", "make-or-buy", "funnel", "voucher", "e-ticket",
                   "Everyday", "SLA", "Work Breakdown"):
        assert banned not in text, banned
    lowered = text.lower()
    for out_of_scope in ("fornecedores de peças", "fornecedor de peças", "peças de reposição", "meta de venda",
                         "metas de vendas"):
        assert out_of_scope not in lowered, out_of_scope


def test_norms_formatting_is_applied(doc) -> None:
    normal = doc.styles["Normal"]
    assert normal.font.name == "Times New Roman" and normal.font.size.pt == 12
    assert normal.paragraph_format.line_spacing_rule == WD_LINE_SPACING.ONE_POINT_FIVE
    assert normal.paragraph_format.alignment == WD_ALIGN_PARAGRAPH.JUSTIFY
    assert len(doc.inline_shapes) >= 10


def test_concept_scores_are_recomputed_correctly() -> None:
    scores = gr.concept_scores()
    assert scores["A"] == pytest.approx(3.30) and scores["B"] == pytest.approx(4.60)
    assert scores["C"] == pytest.approx(3.35)
    assert gr.concept_winner_range()[2] is True
    with pytest.raises(ValueError):
        gr.concept_scores({"a": 0.5, "b": 0.6})


def test_cover_keeps_private_team_data_out_of_the_example_file() -> None:
    import json

    example = json.loads((ROOT / "report" / "team.example.json").read_text(encoding="utf-8"))
    assert all(m["ra"] == "000000" for m in example["members"])


def test_report_uses_no_em_dash(doc) -> None:
    assert not any("—" in t for t in _texts(doc))


def test_table_columns_fit_words_without_shrinking_below_readable_size() -> None:
    from src.docx_builder import fit_columns, text_width_cm

    headers = ["Política", "Custo por devolução", "Simplicidade (15%)", "Nota"]
    rows = [["Frete gratuito", "R$ 12,50", "4", "3,10"]]
    widths = [3.6, 2.1, 1.7, 1.2]
    fonts, new_widths = fit_columns(headers, rows, widths, 8.5)
    assert abs(sum(new_widths) - sum(widths)) < 1e-6
    assert min(fonts) >= 7
    for i, head in enumerate(headers):
        longest = max(head.split(), key=lambda w: text_width_cm(w, fonts[i]))
        assert text_width_cm(longest, fonts[i]) + 0.45 <= new_widths[i] + 1e-6, head
