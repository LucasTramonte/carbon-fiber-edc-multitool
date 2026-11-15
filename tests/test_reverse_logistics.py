"""Tests for the reverse-logistics planning model (report section 6)."""

from pathlib import Path

import pandas as pd
import pytest

from src import reverse_logistics_model as rl

ROOT = Path(__file__).resolve().parents[1]
ASSUMPTIONS = ROOT / "data" / "reverse_logistics_assumptions.csv"


@pytest.fixture(scope="module")
def p() -> dict:
    return rl.load_assumptions(ASSUMPTIONS)


def test_assumptions_have_valid_types_and_ranges(p: dict) -> None:
    table = pd.read_csv(ASSUMPTIONS)
    assert set(table["evidence_type"]) <= {"observed", "derived", "assumed"}
    assert table["parameter"].is_unique
    assert p["lot_units"] == 2000
    assert 0 <= p["voucher_redemption_rate"] <= 1
    shares = sum(p[f"grade_{g}_share"] for g in "abcd")
    assert shares == pytest.approx(1.0)


def test_contribution_margin_matches_report(p: dict) -> None:
    assert p["net_price_brl"] - p["variable_cost_brl"] == 119


def test_card_mass_is_volume_times_density_minus_cutouts(p: dict) -> None:
    expected = 85.60 * 53.98 * 2.0 / 1000 * 1.55 * (1 - 0.06)
    assert rl.card_mass_g(p) == pytest.approx(expected)
    assert rl.card_mass_g(p, thickness_mm=1.5) < rl.card_mass_g(p)


def test_nesting_never_exceeds_sheet_area(p: dict) -> None:
    n = rl.cards_per_sheet(p)
    card_area = p["card_length_mm"] * p["card_width_mm"]
    assert n > 0
    assert n * card_area <= p["sheet_length_mm"] * p["sheet_width_mm"]


def test_mass_balance_closes(p: dict) -> None:
    flows = rl.mass_flows(p)
    for row in flows.itertuples():
        assert row.sheet_mass_kg == pytest.approx(row.card_mass_kg + row.machining_scrap_kg)
        assert row.returned_kg == pytest.approx(
            row.returned_units * row.card_mass_g / 1000
        )
        assert 0 < row.scrap_share < 1


def test_machining_scrap_exceeds_returned_mass_in_all_scenarios(p: dict) -> None:
    flows = rl.mass_flows(p)
    assert (flows["machining_scrap_kg"] > flows["returned_kg"]).all()


def test_cost_table_is_non_negative_and_ordered(p: dict) -> None:
    table = rl.return_cost_table(p)
    assert (table["cost_per_return_brl"] >= 0).all()
    ref = table[table["return_rate"] == p["return_rate_ref"]].set_index("option")
    assert ref.loc["sem_beneficio", "cost_per_return_brl"] < ref.loc["frete_gratis", "cost_per_return_brl"]
    assert ref.loc["frete_gratis", "cost_per_return_brl"] < ref.loc["frete_gratis_voucher", "cost_per_return_brl"]
    assert ref.loc["frete_gratis_voucher", "cost_per_return_brl"] < ref.loc["frete_gratis_dinheiro", "cost_per_return_brl"]


def test_voucher_option_cost_formula(p: dict) -> None:
    table = rl.return_cost_table(p)
    row = table[(table["option"] == "frete_gratis_voucher")
                & (table["return_rate"] == p["return_rate_ref"])].iloc[0]
    expected = (p["reverse_freight_brl"] + p["return_kit_brl"] + p["triage_brl"]
                + p["voucher_brl"] * p["voucher_redemption_rate"])
    assert row["cost_per_return_brl"] == pytest.approx(expected)
    assert row["returned_units"] == pytest.approx(p["lot_units"] * p["return_rate_ref"])
    assert row["share_of_contribution_margin"] < 0.2


def test_decision_weights_sum_to_one_and_scores_in_range(p: dict) -> None:
    for matrix in (rl.benefit_matrix(p), rl.channel_matrix(p)):
        weights = matrix.attrs["weights"]
        assert sum(weights.values()) == pytest.approx(1.0)
        scores = matrix[list(weights)]
        assert ((scores >= 1) & (scores <= 5)).all().all()
        assert matrix["weighted_score"].max() <= 5


def test_cost_weight_sensitivity_returns_winner_per_weight(p: dict) -> None:
    sens = rl.weight_sensitivity(rl.benefit_matrix(p), "custo")
    assert {"cost_weight", "winner"} <= set(sens.columns)
    assert sens["cost_weight"].between(0, 1).all()


def test_store_channel_cost_explodes_with_few_returns(p: dict) -> None:
    channels = rl.channel_cost_table(p)
    stores = channels[channels["channel"] == "lojas_parceiras"].set_index("return_rate")
    assert stores.loc[p["return_rate_low"], "cost_per_return_brl"] > stores.loc[
        p["return_rate_high"], "cost_per_return_brl"
    ]
    assert (stores["returns_per_store_per_month"] < 5).all()


def test_remanufacturing_threshold_is_cost_ratio(p: dict) -> None:
    result = rl.remanufacturing_viability(p)
    assert result["minimum_grade_a_yield"] == pytest.approx(
        (p["triage_brl"] + p["rework_cost_brl"]) / p["variable_cost_brl"]
    )
    assert result["cost_per_recovered_card_brl"] > p["variable_cost_brl"]


def test_schedule_precedence_is_acyclic_and_complete(p: dict) -> None:
    schedule = rl.build_schedule(p)
    ids = set(schedule["id"])
    assert len(schedule) == 7
    for preds in schedule["predecessors"]:
        for pred in filter(None, (x.strip() for x in preds.split(";"))):
            assert pred in ids
    by_id = schedule.set_index("id")
    for ident, preds in schedule.set_index("id")["predecessors"].items():
        for pred in filter(None, (x.strip() for x in preds.split(";"))):
            assert by_id.loc[ident, "start_week"] > by_id.loc[pred, "end_week"]
    assert (schedule["cost_brl"] >= 0).all()


def test_pipeline_writes_outputs(tmp_path: Path) -> None:
    rl.run(ASSUMPTIONS, tmp_path)
    for name in (
        "reverse_logistics_cost_scenarios.csv",
        "reverse_logistics_channels.csv",
        "reverse_logistics_mass_flows.csv",
        "reverse_logistics_decision_matrices.csv",
        "reverse_logistics_schedule.csv",
    ):
        assert (tmp_path / "tables" / name).exists()
    for name in ("reverse_flow.png", "reverse_cost_scenarios.png", "reverse_mass_flows.png"):
        assert (tmp_path / "visualizations" / name).exists()


def test_end_of_life_unit_cost_spreads_the_phase_cost_over_the_lot() -> None:
    p = rl.load_assumptions()
    phase = rl.build_schedule(p)
    assert rl.end_of_life_unit_cost(p) == pytest.approx(phase["cost_brl"].sum() / p["lot_units"])
    assert 0 < rl.end_of_life_unit_cost(p) < p["net_price_brl"] - p["variable_cost_brl"]
