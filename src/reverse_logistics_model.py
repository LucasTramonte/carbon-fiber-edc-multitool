"""Planning model for the product discontinuation phase (report section 6).

Every number comes from ``data/reverse_logistics_assumptions.csv``, where each
row is labelled observed, derived, or assumed. The model produces scenario
tables and figures; it never presents an assumed value as an observation.
"""

from __future__ import annotations

import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

try:  # package import (tests, python -m) or direct script execution
    from src.regional_market_analysis import DATA_DIR, load_state_indicators
except ImportError:  # pragma: no cover
    from regional_market_analysis import DATA_DIR, load_state_indicators

ROOT = Path(__file__).resolve().parents[1]
ASSUMPTIONS_PATH = DATA_DIR / "reverse_logistics_assumptions.csv"
OUTPUT_DIR = ROOT / "outputs"

DARK, ORANGE, GREY, LIGHT = "#263238", "#ef6c00", "#90a4ae", "#eceff1"

BENEFIT_OPTIONS = {
    "sem_beneficio": "Sem benefício (cliente paga o frete)",
    "frete_gratis": "Frete reverso gratuito",
    "frete_gratis_voucher": "Frete gratuito + voucher",
    "frete_gratis_dinheiro": "Frete gratuito + reembolso em dinheiro",
}


def load_assumptions(path: Path = ASSUMPTIONS_PATH) -> dict[str, float]:
    """Load the labelled assumptions as a parameter-to-float mapping."""
    table = pd.read_csv(path)
    if not table["parameter"].is_unique:
        raise ValueError("Assumption parameters must be unique.")
    if not set(table["evidence_type"]) <= {"observed", "derived", "assumed"}:
        raise ValueError("evidence_type must be observed, derived, or assumed.")
    return dict(zip(table["parameter"], table["value"].astype(float)))


def end_of_life_unit_cost(p: dict) -> float:
    """End-of-life phase cost (project plus operation) spread over the units of the lot."""
    return float(build_schedule(p)["cost_brl"].sum() / p["lot_units"])


def return_rates(p: dict) -> list[float]:
    """Return the four scenario return rates in ascending order."""
    return sorted(
        {p["return_rate_low"], p["return_rate_mid"], p["return_rate_ref"], p["return_rate_high"]}
    )


# --------------------------------------------------------------------- mass
def card_mass_g(p: dict, thickness_mm: float | None = None) -> float:
    """Mass of one card in grams: plan area x thickness x density, minus cut-outs."""
    thickness = p["card_thickness_mm"] if thickness_mm is None else thickness_mm
    volume_cm3 = p["card_length_mm"] * p["card_width_mm"] * thickness / 1000
    return volume_cm3 * p["density_g_cm3"] * (1 - p["cutout_area_fraction"])


def cards_per_sheet(p: dict) -> int:
    """Rectangular grid nesting on the usable area, best of two orientations."""
    usable_l = p["sheet_length_mm"] - 2 * p["sheet_edge_margin_mm"]
    usable_w = p["sheet_width_mm"] - 2 * p["sheet_edge_margin_mm"]
    kerf = p["cut_kerf_mm"]

    def fit(span: float, size: float) -> int:
        return max(0, int(math.floor((span + kerf) / (size + kerf))))

    a = fit(usable_l, p["card_length_mm"]) * fit(usable_w, p["card_width_mm"])
    b = fit(usable_l, p["card_width_mm"]) * fit(usable_w, p["card_length_mm"])
    return max(a, b)


def mass_flows(p: dict) -> pd.DataFrame:
    """Mass of cured sheet, cards, machining scrap, and returned cards."""
    per_sheet = cards_per_sheet(p)
    sheets = math.ceil(p["lot_units"] / per_sheet)
    rows = []
    for thickness in (p["card_thickness_mm"], p["card_thickness_alt_mm"]):
        mass_g = card_mass_g(p, thickness)
        sheet_kg = (p["sheet_length_mm"] * p["sheet_width_mm"] * thickness / 1000
                    * p["density_g_cm3"] / 1000) * sheets
        cards_kg = p["lot_units"] * mass_g / 1000
        scrap_kg = sheet_kg - cards_kg
        for rate in return_rates(p):
            units = p["lot_units"] * rate
            returned_kg = units * mass_g / 1000
            rows.append(
                {
                    "thickness_mm": thickness,
                    "card_mass_g": mass_g,
                    "cards_per_sheet": per_sheet,
                    "sheets_per_lot": sheets,
                    "sheet_mass_kg": sheet_kg,
                    "card_mass_kg": cards_kg,
                    "machining_scrap_kg": scrap_kg,
                    "scrap_share": scrap_kg / sheet_kg,
                    "return_rate": rate,
                    "returned_units": units,
                    "returned_kg": returned_kg,
                    "returned_grade_c_d_kg": returned_kg * (p["grade_c_share"] + p["grade_d_share"]),
                    "scrap_to_returned_ratio": scrap_kg / returned_kg,
                }
            )
    return pd.DataFrame(rows)


# --------------------------------------------------------------- benefit cost
def _benefit_unit_cost(p: dict, option: str) -> float:
    base = p["triage_brl"]
    freight = p["reverse_freight_brl"] + p["return_kit_brl"]
    if option == "sem_beneficio":
        return base
    if option == "frete_gratis":
        return base + freight
    if option == "frete_gratis_voucher":
        return base + freight + p["voucher_brl"] * p["voucher_redemption_rate"]
    if option == "frete_gratis_dinheiro":
        return base + freight + p["cash_benefit_brl"]
    raise KeyError(option)


def return_cost_table(p: dict) -> pd.DataFrame:
    """Cost of the collection programme by benefit option and return rate."""
    margin = p["net_price_brl"] - p["variable_cost_brl"]
    rows = []
    for option in BENEFIT_OPTIONS:
        unit = _benefit_unit_cost(p, option)
        for rate in return_rates(p):
            units = p["lot_units"] * rate
            total = unit * units
            per_sold = total / p["lot_units"]
            break_even = math.ceil(p["development_budget_brl"] / (margin - per_sold))
            rows.append(
                {
                    "option": option,
                    "return_rate": rate,
                    "returned_units": units,
                    "cost_per_return_brl": unit,
                    "total_cost_brl": total,
                    "cost_per_unit_sold_brl": per_sold,
                    "share_of_contribution_margin": per_sold / margin,
                    "break_even_units_54000": break_even,
                    "exceeds_management_reserve": total > p["management_reserve_brl"],
                }
            )
    return pd.DataFrame(rows)


# --------------------------------------------------------------------- channels
def southeast_south_population_share() -> float:
    """Upper bound of population reachable by a Southeast/South store pilot."""
    state = load_state_indicators()
    region = state[state["region"].isin(["Southeast", "South"])]
    return float(region["population"].sum() / state["population"].sum())


def channel_cost_table(p: dict) -> pd.DataFrame:
    """Cost per returned card for mail versus a partner-store pilot."""
    quarters = p["horizon_months"] / 3
    rows = []
    for rate in return_rates(p):
        units = p["lot_units"] * rate
        mail = p["reverse_freight_brl"] + p["return_kit_brl"]
        stores = (
            p["partner_store_fee_brl"]
            + p["partner_setup_brl"] * p["partner_stores"] / units
            + p["partner_consolidation_shipment_brl"] * p["partner_stores"] * quarters / units
        )
        rows.append(
            {"channel": "correios_reversa", "return_rate": rate, "returned_units": units,
             "cost_per_return_brl": mail,
             "returns_per_store_per_month": float("nan")}
        )
        rows.append(
            {"channel": "lojas_parceiras", "return_rate": rate, "returned_units": units,
             "cost_per_return_brl": stores,
             "returns_per_store_per_month": units / (p["partner_stores"] * p["horizon_months"])}
        )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- decision matrices
def _rescale(cost: pd.Series) -> pd.Series:
    """Map cost to a 1-5 score: cheapest = 5, most expensive = 1."""
    span = cost.max() - cost.min()
    if span == 0:
        return pd.Series(3.0, index=cost.index)
    return 5 - 4 * (cost - cost.min()) / span


def _weighted(matrix: pd.DataFrame, weights: dict[str, float]) -> pd.DataFrame:
    matrix["weighted_score"] = sum(matrix[k] * w for k, w in weights.items())
    matrix.attrs["weights"] = dict(weights)
    return matrix


def benefit_matrix(p: dict) -> pd.DataFrame:
    """Decision 1: weighted comparison of customer benefits (team judgement + cost)."""
    weights = {"custo": 0.30, "estimulo": 0.30, "simplicidade": 0.15,
               "mensagem": 0.15, "recompra": 0.10}
    cost = pd.Series({o: _benefit_unit_cost(p, o) for o in BENEFIT_OPTIONS})
    judged = {  # 1-5; stimulus follows Harden et al. 2024 and the MSOM take-back findings
        "sem_beneficio": (1, 5, 2, 1),
        "frete_gratis": (3, 4, 4, 2),
        "frete_gratis_voucher": (4, 3, 4, 5),
        "frete_gratis_dinheiro": (5, 2, 3, 1),
    }
    matrix = pd.DataFrame(
        {
            "option": list(BENEFIT_OPTIONS),
            "cost_per_return_brl": cost.values,
            "custo": _rescale(cost).values,
            "estimulo": [judged[o][0] for o in BENEFIT_OPTIONS],
            "simplicidade": [judged[o][1] for o in BENEFIT_OPTIONS],
            "mensagem": [judged[o][2] for o in BENEFIT_OPTIONS],
            "recompra": [judged[o][3] for o in BENEFIT_OPTIONS],
        }
    )
    matrix.insert(0, "decision", "beneficio_ao_cliente")
    return _weighted(matrix, weights)


def channel_matrix(p: dict) -> pd.DataFrame:
    """Decision 2: weighted comparison of collection channels."""
    weights = {"custo": 0.25, "cobertura": 0.30, "rastreabilidade": 0.20,
               "seguranca": 0.15, "esforco": 0.10}
    costs = channel_cost_table(p)
    ref = costs[np.isclose(costs["return_rate"], p["return_rate_ref"])].set_index("channel")
    mail = float(ref.loc["correios_reversa", "cost_per_return_brl"])
    stores = float(ref.loc["lojas_parceiras", "cost_per_return_brl"])
    # a single presential point (home city) has no shipping cost but no national reach
    cost = pd.Series({"correios_reversa": mail, "lojas_parceiras": stores,
                      "ponto_unico_presencial": p["triage_brl"]})
    coverage = pd.Series({"correios_reversa": 1.0,
                          "lojas_parceiras": southeast_south_population_share(),
                          "ponto_unico_presencial": 0.0})
    judged = {"correios_reversa": (5, 4, 4), "lojas_parceiras": (3, 2, 2),
              "ponto_unico_presencial": (4, 4, 3)}
    matrix = pd.DataFrame(
        {
            "option": cost.index,
            "cost_per_return_brl": cost.values,
            "coverage_upper_bound": coverage.values,
            "custo": _rescale(cost).values,
            "cobertura": (1 + 4 * coverage).values,
            "rastreabilidade": [judged[o][0] for o in cost.index],
            "seguranca": [judged[o][1] for o in cost.index],
            "esforco": [judged[o][2] for o in cost.index],
        }
    )
    matrix.insert(0, "decision", "canal_de_recolhimento")
    return _weighted(matrix, weights)


def weight_sensitivity(matrix: pd.DataFrame, criterion: str) -> pd.DataFrame:
    """Winner when one criterion weight varies and the others rescale proportionally."""
    weights = matrix.attrs["weights"]
    others = {k: v for k, v in weights.items() if k != criterion}
    other_total = sum(others.values())
    rows = []
    for w in np.round(np.arange(0.0, 0.801, 0.05), 2):
        scaled = {k: v / other_total * (1 - w) for k, v in others.items()}
        scaled[criterion] = float(w)
        score = sum(matrix[k] * v for k, v in scaled.items())
        rows.append({"cost_weight": float(w), "winner": matrix.loc[score.idxmax(), "option"],
                     "best_score": float(score.max())})
    return pd.DataFrame(rows)


# ------------------------------------------------------------ remanufacturing
def remanufacturing_viability(p: dict) -> dict[str, float]:
    """Compare reworking a returned card with making a new one."""
    rework = p["triage_brl"] + p["rework_cost_brl"]
    return {
        "rework_and_triage_brl": rework,
        "cost_per_recovered_card_brl": rework / p["grade_a_share"],
        "new_card_variable_cost_brl": p["variable_cost_brl"],
        "minimum_grade_a_yield": rework / p["variable_cost_brl"],
        "assumed_grade_a_yield": p["grade_a_share"],
    }


# ----------------------------------------------------------------- schedule
def build_schedule(p: dict) -> pd.DataFrame:
    """Chapter 12 activities with duration, precedence, resources and cost."""
    person_week = p["team_week_cost_per_person_brl"]
    ref_units = p["lot_units"] * p["return_rate_ref"]
    horizon_weeks = int(round(p["horizon_months"] * 52 / 12))
    opex = _benefit_unit_cost(p, "frete_gratis_voucher") * ref_units
    kits = p["return_kit_brl"] * ref_units
    spec = [
        ("D1", "Analisar e aprovar a descontinuidade", 1, "", "Equipe (2)", 2 * person_week, "projeto"),
        ("D2", "Planejar a descontinuidade", 1, "D1", "Equipe (2)", 2 * person_week, "projeto"),
        ("D3", "Preparar o recebimento (kit, rotina, registro)", 2, "D2", "Equipe (1)",
         1 * 2 * person_week + kits, "projeto"),
        ("D4", "Acompanhar o recebimento (janela de devolução)", horizon_weeks, "D3",
         "Atendimento", opex - kits, "operacional"),
        ("D5", "Descontinuar a produção", 1, "D2", "Produção (2)", 2 * person_week, "projeto"),
        ("D6", "Finalizar suporte ao produto", 1, "D2; D5", "Equipe (1)", person_week, "projeto"),
        ("D7", "Avaliação geral e encerramento", 1, "D4; D6", "Equipe (2)", 2 * person_week, "projeto"),
    ]
    ends: dict[str, int] = {}
    rows = []
    for ident, name, duration, preds, resources, cost, kind in spec:
        pred_ids = [x.strip() for x in preds.split(";") if x.strip()]
        start = max((ends[x] for x in pred_ids), default=0) + 1
        end = start + duration - 1
        ends[ident] = end
        rows.append({"id": ident, "activity": name, "start_week": start,
                     "duration_weeks": duration, "end_week": end, "predecessors": preds or "—",
                     "resources": resources, "cost_brl": round(cost, 2), "cost_type": kind})
    frame = pd.DataFrame(rows)
    frame["predecessors"] = frame["predecessors"].replace("—", "")
    return frame


# ------------------------------------------------------------------ figures
def _flow_figure(path: Path) -> None:
    fig, ax = plt.subplots(figsize=(11, 6))
    ax.set_xlim(0, 11)
    ax.set_ylim(0, 6)
    ax.axis("off")

    def box(x, y, w, h, text, fc=LIGHT, ec=DARK, size=9):
        ax.add_patch(plt.Rectangle((x, y), w, h, fc=fc, ec=ec, lw=1.2))
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=size, wrap=True)

    def arrow(x0, y0, x1, y1):
        ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                    arrowprops={"arrowstyle": "->", "color": DARK, "lw": 1.2})

    box(0.1, 4.6, 1.9, 0.9, "Cliente pede\nretorno (formulário\nou e-mail)")
    box(2.5, 4.6, 1.9, 0.9, "Código de\npostagem reversa\n(validade 30 dias)")
    box(4.9, 4.6, 1.9, 0.9, "Envelope com\nproteção de borda\n+ lote gravado")
    box(7.3, 4.6, 1.9, 0.9, "Recebimento e\nregistro por lote\n(luvas, saco duplo)")
    box(9.4, 4.6, 1.5, 0.9, "Triagem\nvisual e\ndimensional", fc=ORANGE, ec=DARK)
    for x in (2.0, 4.4, 6.8, 9.2):
        arrow(x, 5.05, x + 0.5 if x < 9 else 0.2 + x, 5.05)
    box(0.1, 2.4, 2.4, 1.1, "A · Íntegro\n→ peça de ensaio,\nmostruário (nunca\nrevenda como novo)", size=8.5)
    box(2.9, 2.4, 2.4, 1.1, "B · Desgaste leve\n→ segunda vida SÓ se\nvalidada em ensaio;\nsenão vai para C", size=8.5)
    box(5.7, 2.4, 2.4, 1.1, "C · Delaminado/trincado\n→ consolidação e\nreciclagem (lote\nmínimo a negociar)", size=8.5)
    box(8.5, 2.4, 2.4, 1.1, "D · Fibra exposta/\ncontaminado\n→ saco duplo,\ndestinação licenciada", size=8.5)
    for x in (1.3, 4.1, 6.9, 9.7):
        arrow(10.1, 4.6, x, 3.5)
    box(0.1, 0.4, 5.2, 1.0, "Cliente: voucher emitido após validar o cartão\n(1 por cartão; só fim de vida, defeito segue a garantia)", size=8.5)
    box(5.7, 0.4, 5.2, 1.0, "Registro: lote, massa recebida, classe e destino\n(alimenta o percentual mínimo de recebimento)", size=8.5)
    ax.set_title("Fluxo de logística reversa do cartão", fontsize=12)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def _cost_figure(costs: pd.DataFrame, p: dict, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 5.6))
    options = list(BENEFIT_OPTIONS)
    colors = [GREY, "#546e7a", ORANGE, DARK]
    rates = return_rates(p)
    x = np.arange(len(rates))
    width = 0.2
    for i, option in enumerate(options):
        sub = costs[costs["option"] == option].sort_values("return_rate")
        bars = ax.bar(x + (i - 1.5) * width, sub["total_cost_brl"], width,
                      label=BENEFIT_OPTIONS[option], color=colors[i])
        for bar, value in zip(bars, sub["total_cost_brl"]):
            ax.text(bar.get_x() + bar.get_width() / 2, value + 150, f"{value:,.0f}".replace(",", "."),
                    ha="center", fontsize=7)
    ax.axhline(p["management_reserve_brl"], color="#b71c1c", ls="--", lw=1.2)
    ax.text(-0.45, p["management_reserve_brl"] + 250,
            "Reserva gerencial do projeto: R$ 6.000", color="#b71c1c", ha="left", fontsize=8)
    ax.set_xticks(x, [f"{r:.0%}" + ("\n(ref. ReturPen)" if np.isclose(r, p["return_rate_ref"]) else "")
                      for r in rates])
    ax.set(xlabel="Taxa de devolução do lote de 2.000 un. (hipótese)",
           ylabel="Custo total do recolhimento (R$)",
           title="Custo do recolhimento por benefício e taxa de devolução")
    ax.legend(fontsize=8, loc="upper left")
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def _mass_figure(flows: pd.DataFrame, p: dict, path: Path) -> None:
    sub = flows[np.isclose(flows["thickness_mm"], p["card_thickness_mm"])]
    fig, ax = plt.subplots(figsize=(9, 5.4))
    labels = [f"{r:.0%}" for r in sub["return_rate"]]
    x = np.arange(len(sub))
    ax.bar(x, sub["machining_scrap_kg"], color=DARK, label="Retalhos de usinagem do lote")
    ax.bar(x, sub["returned_kg"], bottom=sub["machining_scrap_kg"], color=ORANGE,
           label="Cartões devolvidos no fim de vida")
    for xi, (s, r) in enumerate(zip(sub["machining_scrap_kg"], sub["returned_kg"])):
        ax.text(xi, s / 2, f"{s:.1f} kg", ha="center", color="white", fontsize=9)
        ax.text(xi, s + r / 2, f"{r:.1f} kg", ha="center", fontsize=9)
    ax.set_xticks(x, labels)
    ax.set(xlabel="Taxa de devolução (hipótese)", ylabel="Massa de compósito curado (kg)",
           title="Massa a destinar por lote de 2.000 cartões (espessura 2 mm)")
    ax.legend(fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


# ---------------------------------------------------------------------- run
def run(assumptions_path: Path = ASSUMPTIONS_PATH, output_dir: Path = OUTPUT_DIR) -> None:
    """Write scenario tables and figures to ``output_dir``."""
    p = load_assumptions(assumptions_path)
    tables = output_dir / "tables"
    figures = output_dir / "visualizations"
    tables.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)

    costs = return_cost_table(p)
    flows = mass_flows(p)
    channels = channel_cost_table(p)
    benefit, channel = benefit_matrix(p), channel_matrix(p)
    matrices = pd.concat([benefit, channel], ignore_index=True)

    costs.to_csv(tables / "reverse_logistics_cost_scenarios.csv", index=False)
    channels.to_csv(tables / "reverse_logistics_channels.csv", index=False)
    flows.to_csv(tables / "reverse_logistics_mass_flows.csv", index=False)
    matrices.to_csv(tables / "reverse_logistics_decision_matrices.csv", index=False)
    build_schedule(p).to_csv(tables / "reverse_logistics_schedule.csv", index=False)
    pd.DataFrame([remanufacturing_viability(p)]).to_csv(
        tables / "reverse_logistics_remanufacturing.csv", index=False)

    try:  # Graphviz renders the workflow; matplotlib is only a fallback
        from src import reverse_flow_diagram
    except ImportError:  # pragma: no cover
        import reverse_flow_diagram
    if not reverse_flow_diagram.render_pngs(p, figures):
        _flow_figure(figures / "reverse_flow.png")
    _cost_figure(costs, p, figures / "reverse_cost_scenarios.png")
    _mass_figure(flows, p, figures / "reverse_mass_flows.png")


def main() -> None:
    """Run the default reverse-logistics model."""
    run()
    print(f"Reverse-logistics outputs saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
