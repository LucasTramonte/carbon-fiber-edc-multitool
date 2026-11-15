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


def test_sales_metrics_roi_irr_and_payback() -> None:
    result = pp.sales_metrics(units=1000, investment=76_110, unit_margin=119)
    assert result["roi"] == pytest.approx((1000 * 119 - 76_110) / 76_110)
    assert result["payback_months"] == pytest.approx(76_110 / (1000 / 12 * 119))
    # the IRR must zero the net present value of the cash flows
    flows = [-76_110] + [1000 / 12 * 119] * 12
    npv = sum(flow / (1 + result["irr_monthly"]) ** t for t, flow in enumerate(flows))
    assert npv == pytest.approx(0, abs=1e-3)


def test_sales_metrics_negative_when_volume_is_below_break_even() -> None:
    result = pp.sales_metrics(units=500, investment=76_110, unit_margin=119)
    assert result["roi"] < 0 and result["irr_monthly"] < 0 and result["payback_months"] > 12
