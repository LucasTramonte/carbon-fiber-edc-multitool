"""Single source of truth for the project plan (report section 2).

Follows the format of the course examples: precedence table
(ID, Atividade, Início, Duração, Término, Precedência), cost table with
resource codes and quantities, standard-cost legend, and weekly baseline.

Every activity total equals the group's original planning estimate
(BRL 54,000). The split by resource type is a planning assumption that must be
replaced by quotations; standard rates are assumptions as well.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isclose

import pandas as pd

# Standard cost (course format "Custo Padrão: Tipo | Custo"), BRL per person-week
# for labour. All rates are planning assumptions pending quotations.
STANDARD_COST = {
    "EQ": ("Equipe de projeto", "Mão de obra", 625.0),
    "PJ": ("Projetista", "Mão de obra", 1000.0),
    "CP": ("Compras", "Mão de obra", 1000.0),
    "PD": ("Produção", "Mão de obra", 1000.0),
    "MK": ("Marketing", "Mão de obra", 1500.0),
}


@dataclass(frozen=True)
class Activity:
    ident: str
    name: str
    weeks: int
    predecessors: tuple[str, ...]
    wbs: str  # deliverable code (1.0 ... 7.0)
    labour: tuple[tuple[str, int], ...] = ()  # (resource code, quantity)
    equipment_services: float = 0.0
    inputs: float = 0.0
    total: float = 0.0  # the group's original estimate for the activity


ACTIVITIES = (
    Activity("A1", "Requisitos e pesquisa primária", 2, (), "1.0", (("EQ", 2),), 0, 0, 2500),
    Activity("A2", "Funções e matriz morfológica", 1, ("A1",), "2.0", (("EQ", 2),), 0, 250, 1500),
    Activity("A3", "CAD, arquitetura e tolerâncias", 2, ("A2",), "3.0", (("PJ", 2),), 1000, 0, 5000),
    Activity("A4", "Cotação e compra de chapa", 2, ("A1",), "3.0", (("CP", 1),), 0, 16000, 18000),
    Activity("A5", "Protótipos usinados", 2, ("A3", "A4"), "4.0", (), 6000, 0, 6000),
    Activity("A6", "Testes e otimização", 2, ("A5",), "4.0", (("EQ", 2),), 1500, 500, 4500),
    Activity("A7", "Processo, embalagem e inspeção", 2, ("A6",), "5.0", (("PD", 2),), 1000, 2000, 7000),
    Activity("A8", "Lançamento piloto", 2, ("A7",), "6.0", (("MK", 1),), 0, 5000, 8000),
    Activity("A9", "Encerramento e lições aprendidas", 1, ("A8",), "7.0", (("EQ", 2),), 250, 0, 1500),
)

DELIVERABLES = {
    "1.0": "Gestão e requisitos",
    "2.0": "Projeto conceitual",
    "3.0": "Projeto detalhado e suprimento",
    "4.0": "Protótipo e testes",
    "5.0": "Preparação da produção",
    "6.0": "Lançamento piloto",
    "7.0": "Encerramento e fim de vida",
}

BUDGET = 54000.0
RESERVE = 6000.0


def labour_cost(activity: Activity) -> float:
    """Labour cost = quantity x weeks x standard rate."""
    return sum(qty * activity.weeks * STANDARD_COST[code][2] for code, qty in activity.labour)


def schedule() -> pd.DataFrame:
    """Forward/backward pass (CPM) in project weeks; slack and critical flag."""
    by_id = {a.ident: a for a in ACTIVITIES}
    es: dict[str, int] = {}
    ef: dict[str, int] = {}
    for a in ACTIVITIES:  # ACTIVITIES is already in topological order
        es[a.ident] = max((ef[p] for p in a.predecessors), default=0) + 1
        ef[a.ident] = es[a.ident] + a.weeks - 1
    end = max(ef.values())
    successors = {a.ident: [b.ident for b in ACTIVITIES if a.ident in b.predecessors] for a in ACTIVITIES}
    lf: dict[str, int] = {}
    ls: dict[str, int] = {}
    for a in reversed(ACTIVITIES):
        lf[a.ident] = min((ls[s] for s in successors[a.ident]), default=end + 1) - 1
        ls[a.ident] = lf[a.ident] - a.weeks + 1
    rows = []
    for a in ACTIVITIES:
        slack = ls[a.ident] - es[a.ident]
        rows.append(
            {"id": a.ident, "activity": a.name, "start_week": es[a.ident], "duration_weeks": a.weeks,
             "end_week": ef[a.ident], "predecessors": ";".join(a.predecessors) or "-",
             "slack_weeks": slack, "critical": slack == 0, "wbs": a.wbs,
             "successors": ";".join(successors[a.ident]) or "-"}
        )
    assert by_id  # keeps linters quiet about the unused helper mapping
    return pd.DataFrame(rows)


def cost_table() -> pd.DataFrame:
    """Cost per activity split by resource type (labour computed, rest assumed)."""
    rows = []
    for a in ACTIVITIES:
        labour = labour_cost(a)
        total = labour + a.equipment_services + a.inputs
        if not isclose(total, a.total, abs_tol=0.01):
            raise ValueError(f"{a.ident}: split {total} differs from estimate {a.total}")
        codes = "; ".join(f"{c} ({q})" for c, q in a.labour) or "-"
        rows.append(
            {"id": a.ident, "activity": a.name, "labour_codes": codes, "labour_brl": labour,
             "equipment_services_brl": a.equipment_services, "inputs_brl": a.inputs,
             "activity_cost_brl": total, "cost_per_week_brl": total / a.weeks}
        )
    return pd.DataFrame(rows)


def weekly_baseline() -> pd.DataFrame:
    """Planned cost per week, spreading each activity evenly over its duration."""
    sched = schedule().set_index("id")
    costs = cost_table().set_index("id")
    horizon = int(sched["end_week"].max())
    weekly = [0.0] * horizon
    for ident in sched.index:
        per_week = costs.loc[ident, "cost_per_week_brl"]
        for week in range(int(sched.loc[ident, "start_week"]), int(sched.loc[ident, "end_week"]) + 1):
            weekly[week - 1] += per_week
    frame = pd.DataFrame({"week": range(1, horizon + 1), "cost_brl": weekly})
    frame["cumulative_brl"] = frame["cost_brl"].cumsum()
    return frame


def critical_path() -> list[str]:
    """Activities with zero slack, in schedule order."""
    table = schedule()
    return table.loc[table["critical"], "id"].tolist()


# ---------------------------------------------------------------- economic viability (Cap. 5)
WEEKS_PER_MONTH = 52 / 12
SALES_WEEKS = 52  # sales are spread evenly over 12 months after the launch
DISCOUNT_RATE = 0.1375  # Selic target, % a.a. (Banco Central do Brasil, SGS series 432): minimum attractive rate


def cash_flows(units: float, unit_net_margin: float, sales_weeks: int = SALES_WEEKS) -> list[float]:
    """Weekly net cash flow: development outlays (the weekly baseline), then the margin of sales.

    ``unit_net_margin`` is the unit price minus variable and end-of-life costs, so the flows change
    sign once. Flow ``i`` falls at the end of project week ``i + 1``.
    """
    outlays = [-cost for cost in weekly_baseline()["cost_brl"]]
    return outlays + [units / sales_weeks * unit_net_margin] * sales_weeks


def npv(flows: list[float], annual_rate: float = DISCOUNT_RATE) -> float:
    """Net present value with weekly compounding equivalent to the annual rate."""
    weekly = (1 + annual_rate) ** (1 / 52) - 1
    return sum(flow / (1 + weekly) ** t for t, flow in enumerate(flows, start=1))


def irr_monthly(flows: list[float]) -> float:
    """Internal rate of return, expressed per month (bisection on the weekly rate)."""
    low, high = -0.5, 5.0
    for _ in range(200):  # the NPV falls as the rate rises
        mid = (low + high) / 2
        value = sum(flow / (1 + mid) ** t for t, flow in enumerate(flows, start=1))
        low, high = (mid, high) if value > 0 else (low, mid)
    return (1 + (low + high) / 2) ** WEEKS_PER_MONTH - 1


def payback_months(flows: list[float]) -> float:
    """Months from the project start until the cumulative flow turns positive (inf if never)."""
    total = 0.0
    for i, flow in enumerate(flows):
        if total < 0 <= total + flow:
            return (i + (-total) / flow) / WEEKS_PER_MONTH
        total += flow
    return float("inf")


def economics(units: float, unit_net_margin: float, annual_rate: float = DISCOUNT_RATE) -> dict[str, float]:
    """ROI over the budget, NPV, monthly IRR and payback for selling ``units`` in 12 months."""
    flows = cash_flows(units, unit_net_margin)
    return {
        "roi": sum(flows) / BUDGET,
        "npv": npv(flows, annual_rate),
        "irr_monthly": irr_monthly(flows),
        "payback_months": payback_months(flows),
    }


def units_for_zero_npv(unit_net_margin: float, annual_rate: float = DISCOUNT_RATE) -> float:
    """Units sold in 12 months at which the NPV is zero (the NPV is linear in the units)."""
    weekly = (1 + annual_rate) ** (1 / 52) - 1
    outlays = weekly_baseline()["cost_brl"]
    pv_outlays = sum(cost / (1 + weekly) ** t for t, cost in enumerate(outlays, start=1))
    start = len(outlays)
    pv_unit = sum(unit_net_margin / SALES_WEEKS / (1 + weekly) ** (start + k) for k in range(1, SALES_WEEKS + 1))
    return pv_outlays / pv_unit
