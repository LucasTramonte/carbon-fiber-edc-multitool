"""Office Math builders and the equations of the economic model."""

from __future__ import annotations

from docx import Document

from src import omml as mm

M = "{http://schemas.openxmlformats.org/officeDocument/2006/math}"


def test_fragments_compose_into_valid_math_elements() -> None:
    fragment = mm.v("m") + mm.n(" = ") + mm.frac(mm.v("Q"), mm.sub(mm.v("T"), mm.v("v")))
    element = mm.math_element(fragment)
    assert element.tag == M + "oMath"
    assert len(list(element.iter(M + "f"))) == 1 and len(list(element.iter(M + "sSub"))) == 1
    display = mm.math_paragraph_element(fragment)
    assert display.tag == M + "oMathPara"


def test_summation_and_cases_have_the_expected_structure() -> None:
    total = mm.math_element(mm.total(mm.n("t = 1"), mm.v("T"), mm.v("F")))
    assert len(list(total.iter(M + "nary"))) == 1
    piecewise = mm.math_element(mm.cases(mm.v("a"), mm.v("b")))
    assert len(list(piecewise.iter(M + "eqArr"))) == 1
    assert len(list(piecewise.iter(M + "e"))) == 3  # the delimiter body and the two rows


def test_text_is_escaped() -> None:
    element = mm.math_element(mm.n("a < b & c"))
    assert "a < b & c" in "".join(node.text or "" for node in element.iter(M + "t"))


def test_builder_numbers_equations_and_keeps_inline_math(tmp_path) -> None:
    from src.docx_builder import Builder

    b = Builder()
    b.equation(mm.v("x") + mm.n(" = 1"))
    b.equation(mm.v("y") + mm.n(" = 2"))
    b.math_para(["onde ", (mm.v("x"),), " vale 1"])
    assert b.eq_no == 2
    body = b.doc.element.body
    assert len(list(body.iter(M + "oMathPara"))) == 2 and len(list(body.iter(M + "oMath"))) == 3
    path = tmp_path / "eq.docx"
    b.doc.save(path)
    reopened = Document(path)
    assert len(list(reopened.element.body.iter(M + "oMath"))) == 3
