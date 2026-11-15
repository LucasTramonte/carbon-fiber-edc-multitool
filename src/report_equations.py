"""The cash-flow model as native Word equations, shared by the Portuguese and the English report.

Both editions print the same seven numbered equations (net unit margin, weekly cash flow, NPV, IRR, ROI, payback
and NPV break-even); only the words inside them change ("para"/"for", "com"/"with", "VPL"/"NPV", "TIR"/"IRR").
The numbers behind them live in ``project_plan`` (``cash_flows``, ``npv``, ``irr_monthly``, ``payback_months``,
``economics``, ``units_for_zero_npv``); this module only typesets the model.
"""

from __future__ import annotations

try:
    from src import omml as mm
except ImportError:  # pragma: no cover
    import omml as mm

V, N, SUB, SUP, FR, SUM, PAR = mm.v, mm.n, mm.sub, mm.sup, mm.frac, mm.total, mm.paren
F_t, C_t = SUB(V("F"), V("t")), SUB(V("C"), V("t"))
T_d, T_v, i_s = SUB(V("T"), V("d")), SUB(V("T"), V("v")), SUB(V("i"), V("s"))
r_star = SUP(V("r"), N("*"))

TERMS = {
    "pt": {"for": "para", "with": "com", "npv": "VPL", "irr": "TIR"},
    "en": {"for": "for", "with": "with", "npv": "NPV", "irr": "IRR"},
}


def discounted(rate: str) -> str:
    """The factor (1 + rate)^t."""
    return SUP(PAR(N("1 + ") + rate), V("t"))


def add_equations(b, lang: str) -> None:
    """Add the seven numbered equations of the economic model to the builder ``b``."""
    w = TERMS[lang]
    minus, dot = mm.MINUS, mm.CDOT
    b.equation(V("m") + N(" = ") + V("p") + N(f" {minus} ") + SUB(V("c"), V("v")) + N(f" {minus} ")
               + SUB(V("c"), V("f")))
    b.equation(F_t + N(" = ") + mm.cases(
        N(minus) + C_t + N(f",   {w['for']}   1 ≤ ") + V("t") + N(" ≤ ") + T_d,
        FR(V("Q"), T_v) + N(f" {dot} ") + V("m") + N(f",   {w['for']}   ") + T_d + N(" < ") + V("t")
        + N(" ≤ ") + V("T")))
    b.equation(N(f"{w['npv']} = ") + SUM(N("t = 1"), V("T"), FR(F_t, discounted(i_s))) + N(f",   {w['with']}   ")
               + i_s + N(" = ") + SUP(PAR(N("1 + ") + V("i")), FR(N("1"), N("52"))) + N(f" {minus} 1"))
    b.equation(SUM(N("t = 1"), V("T"), FR(F_t, discounted(r_star))) + N(" = 0,   ") + N(f"{w['irr']} = ")
               + SUP(PAR(N("1 + ") + r_star), FR(N("52"), N("12"))) + N(f" {minus} 1"))
    b.equation(N("ROI = ") + FR(SUM(N("t = 1"), V("T"), F_t), V("I")) + N(" = ")
               + FR(V("Q") + N(f" {dot} ") + V("m") + N(f" {minus} ") + V("I"), V("I")))
    b.equation(V("τ") + N(" = min") + PAR(V("k") + N(" : ") + SUM(N("t = 1"), V("k"), F_t) + N(" ≥ 0"), "{", "}"))
    b.equation(SUB(V("Q"), N(f"{w['npv']}=0")) + N(" = ") + FR(
        SUM(N("t = 1"), T_d, C_t + SUP(PAR(N("1 + ") + i_s), N(minus) + V("t"))),
        FR(V("m"), T_v) + SUM(V("t") + N(" = ") + T_d + N(" + 1"), V("T"),
                              SUP(PAR(N("1 + ") + i_s), N(minus) + V("t")))))
