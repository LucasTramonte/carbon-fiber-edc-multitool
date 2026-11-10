"""Tests for regional analysis contracts and output generation."""

from pathlib import Path

import pandas as pd
import pytest

from src.regional_market_analysis import (
    build_financial_sensitivity,
    build_project_schedule,
    build_regional_analysis,
    load_state_indicators,
    run_analysis,
)


def test_regional_analysis_preserves_population_share() -> None:
    states = pd.DataFrame(
        {
            "state_code": [35, 31, 41],
            "population": [10, 5, 2],
            "income": [100, 50, 80],
            "state": ["SP", "MG", "PR"],
            "region": ["Southeast", "Southeast", "South"],
        }
    )

    result = build_regional_analysis(states)

    assert result["population_2024"].sum() == 17
    assert result.loc[result["region"] == "Southeast", "weighted_mean_income_brl"].item() == 83.33


def test_load_state_indicators_rejects_missing_state(tmp_path: Path) -> None:
    pd.DataFrame({"D1C": [35], "V": [10]}).to_csv(
        tmp_path / "ibge_state_population.csv", index=False
    )
    pd.DataFrame({"D1C": [35], "V": [100]}).to_csv(
        tmp_path / "ibge_state_income.csv", index=False
    )

    with pytest.raises(ValueError, match="27 states"):
        load_state_indicators(tmp_path)


def test_pipeline_writes_tables_and_visualizations(tmp_path: Path) -> None:
    population = pd.DataFrame({"D1C": list(range(11, 18)) + [21, 22, 23, 24, 25, 26, 27, 28, 29,
        31, 32, 33, 35, 41, 42, 43, 50, 51, 52, 53], "V": [100] * 27})
    income = pd.DataFrame({"D1C": population["D1C"], "V": [50] * 27})
    population.to_csv(tmp_path / "ibge_state_population.csv", index=False)
    income.to_csv(tmp_path / "ibge_state_income.csv", index=False)

    run_analysis(tmp_path, tmp_path / "outputs")

    assert (tmp_path / "outputs" / "tables" / "regional_market_analysis_2024.csv").exists()
    assert (tmp_path / "outputs" / "visualizations" / "regional_income_2024.png").exists()


def test_financial_and_schedule_outputs_have_expected_contracts() -> None:
    financial = build_financial_sensitivity()
    schedule = build_project_schedule()

    assert (financial["unit_contribution_margin_brl"] > 0).all()
    assert len(schedule) == 10
    assert {"id", "predecessors", "cost_brl"} <= set(schedule.columns)
