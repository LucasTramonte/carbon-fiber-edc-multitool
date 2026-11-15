"""Minimal builders for Office Math (OMML), so equations are native, editable Word equations.

Each helper returns an XML fragment (a string); fragments compose by concatenation. ``math_element`` and
``math_paragraph_element`` wrap a fragment into an element that can be appended to a ``w:p``.

Letters are italic by default, as in Word's math zones; ``n`` writes upright text (function names, units,
words). Example: ``frac(v("Q"), sub(v("T"), v("v")))`` is Q over T_v.
"""

from __future__ import annotations

from xml.sax.saxutils import escape

from docx.oxml import parse_xml

M_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

MINUS = "−"
CDOT = "·"


def _run(text: str, upright: bool) -> str:
    properties = '<m:rPr><m:sty m:val="p"/></m:rPr>' if upright else ""
    return f'<m:r>{properties}<m:t xml:space="preserve">{escape(text)}</m:t></m:r>'


def v(text: str) -> str:
    """Variable: italic."""
    return _run(text, upright=False)


def n(text: str) -> str:
    """Upright text: numbers, operators, function names and words."""
    return _run(text, upright=True)


def seq(*parts: str) -> str:
    return "".join(parts)


def sub(base: str, lower: str) -> str:
    return f"<m:sSub><m:e>{base}</m:e><m:sub>{lower}</m:sub></m:sSub>"


def sup(base: str, upper: str) -> str:
    return f"<m:sSup><m:e>{base}</m:e><m:sup>{upper}</m:sup></m:sSup>"


def frac(numerator: str, denominator: str) -> str:
    return f"<m:f><m:num>{numerator}</m:num><m:den>{denominator}</m:den></m:f>"


def total(lower: str, upper: str, body: str) -> str:
    """Summation with limits above and below."""
    return ('<m:nary><m:naryPr><m:chr m:val="∑"/><m:limLoc m:val="undOvr"/></m:naryPr>'
            f"<m:sub>{lower}</m:sub><m:sup>{upper}</m:sup><m:e>{body}</m:e></m:nary>")


def paren(inner: str, opening: str = "(", closing: str = ")") -> str:
    return (f'<m:d><m:dPr><m:begChr m:val="{opening}"/><m:endChr m:val="{closing}"/></m:dPr>'
            f"<m:e>{inner}</m:e></m:d>")


def cases(*rows: str) -> str:
    """Piecewise definition: a left brace and one row per case."""
    body = "".join(f"<m:e>{row}</m:e>" for row in rows)
    return ('<m:d><m:dPr><m:begChr m:val="{"/><m:endChr m:val=""/></m:dPr><m:e>'
            f'<m:eqArr><m:eqArrPr><m:baseJc m:val="center"/></m:eqArrPr>{body}</m:eqArr></m:e></m:d>')


def _wrap(tag: str, fragment: str):
    return parse_xml(f'<{tag} xmlns:m="{M_NS}" xmlns:w="{W_NS}">{fragment}</{tag}>')


def math_element(fragment: str):
    """Inline math (``m:oMath``) to append to a paragraph between text runs."""
    return _wrap("m:oMath", fragment)


def math_paragraph_element(fragment: str):
    """Display math (``m:oMathPara``): put it alone in a paragraph."""
    return parse_xml(f'<m:oMathPara xmlns:m="{M_NS}" xmlns:w="{W_NS}"><m:oMath>{fragment}</m:oMath></m:oMathPara>')
