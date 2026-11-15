"""Tests for the project plan (report section 2)."""

import pytest

from src import project_plan as pp


def test_activity_totals_sum_to_budget() -> None:
    assert sum(a.total for a in pp.ACTIVITIES) == pp.BUDGET == 54000


def test_cost_split_reproduces_every_activity_total() -> None:
    table = pp.cost_table()
    assert table["activity_cost_brl"].sum() == pytest.approx(54000)
    for a in pp.ACTIVITIES:
        row = table[table["id"] == a.ident].iloc[0]
        assert row["labour_brl"] + row["equipment_services_brl"] + row["inputs_brl"] == pytest.approx(a.total)


def test_schedule_matches_report_critical_path_and_slack() -> None:
    s = pp.schedule().set_index("id")
    assert s["end_week"].max() == 14
    assert pp.critical_path() == ["A1", "A2", "A3", "A5", "A6", "A7", "A8", "A9"]
    assert s.loc["A4", "slack_weeks"] == 1 and not s.loc["A4", "critical"]
    assert (s["slack_weeks"] >= 0).all()


def test_precedence_constraints_hold() -> None:
    s = pp.schedule().set_index("id")
    for a in pp.ACTIVITIES:
        for p in a.predecessors:
            assert s.loc[a.ident, "start_week"] > s.loc[p, "end_week"]


def test_baseline_is_cumulative_and_reaches_budget() -> None:
    b = pp.weekly_baseline()
    assert b["cumulative_brl"].iloc[-1] == pytest.approx(54000)
    assert b["cumulative_brl"].is_monotonic_increasing
    assert len(b) == 14
    assert b.loc[b["week"] == 4, "cumulative_brl"].item() == pytest.approx(24500)


def test_every_activity_belongs_to_a_deliverable() -> None:
    assert {a.wbs for a in pp.ACTIVITIES} <= set(pp.DELIVERABLES)
    assert set(pp.DELIVERABLES) == {a.wbs for a in pp.ACTIVITIES}


def test_cash_flows_start_with_the_development_outlays_and_change_sign_once() -> None:
    flows = pp.cash_flows(units=1000, unit_net_margin=107.9)
    assert sum(flows[:14]) == pytest.approx(-pp.BUDGET)
    assert len(flows) == 14 + pp.SALES_WEEKS
    signs = [flow > 0 for flow in flows]
    assert signs.count(True) == pp.SALES_WEEKS and signs[:14] == [False] * 14


def test_economics_roi_npv_irr_and_payback_are_consistent() -> None:
    margin = 107.9
    result = pp.economics(1000, margin)
    assert result["roi"] == pytest.approx((1000 * margin - pp.BUDGET) / pp.BUDGET)
    flows = pp.cash_flows(1000, margin)
    assert result["npv"] == pytest.approx(pp.npv(flows))
    weekly = (1 + result["irr_monthly"]) ** (1 / pp.WEEKS_PER_MONTH) - 1
    assert sum(f / (1 + weekly) ** t for t, f in enumerate(flows, start=1)) == pytest.approx(0, abs=1e-3)
    assert 14 / pp.WEEKS_PER_MONTH < result["payback_months"] < (14 + pp.SALES_WEEKS) / pp.WEEKS_PER_MONTH


def test_more_units_means_better_economics() -> None:
    low, high = pp.economics(600, 107.9), pp.economics(2000, 107.9)
    assert high["roi"] > low["roi"] and high["npv"] > low["npv"]
    assert high["irr_monthly"] > low["irr_monthly"] and high["payback_months"] < low["payback_months"]


def test_units_for_zero_npv_zeroes_the_npv() -> None:
    units = pp.units_for_zero_npv(107.9)
    assert pp.npv(pp.cash_flows(units, 107.9)) == pytest.approx(0, abs=1e-3)
    # discounting makes the NPV break-even higher than the undiscounted one
    assert units > pp.BUDGET / 107.9


def test_payback_is_infinite_when_sales_never_recover_the_investment() -> None:
    assert pp.payback_months(pp.cash_flows(100, 107.9)) == float("inf")
