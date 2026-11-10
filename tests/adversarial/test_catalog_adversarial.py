"""Adversarial tests for untrusted manually collected catalog values."""

from pathlib import Path

import pandas as pd
import pytest

from src.analyze_manual_catalog import load_observations, parse_price, write_outputs
from tests.test_manual_catalog import observation


def test_negative_and_non_numeric_prices_are_not_accepted(tmp_path: Path) -> None:
    rows = [
        observation(url="https://example.com/negative", displayed_price="-R$ 1,00"),
        observation(url="https://example.com/text", displayed_price="free"),
    ]
    path = tmp_path / "untrusted.csv"
    pd.DataFrame(rows).to_csv(path, index=False)

    assert load_observations(path).empty


def test_formula_like_text_is_preserved_as_data_not_executed(tmp_path: Path) -> None:
    row = observation(
        title="=HYPERLINK(\"https://attacker.invalid\",\"click\")",
        url="https://example.com/safe",
    )
    path = tmp_path / "formula.csv"
    pd.DataFrame([row]).to_csv(path, index=False)

    loaded = load_observations(path)
    write_outputs(loaded, tmp_path / "outputs")

    assert loaded.iloc[0]["title"].startswith("=")
    assert (tmp_path / "outputs" / "valid_observations.csv").exists()


@pytest.mark.parametrize("value", ["", "n/a", "not informed", "garbage", "-1"])
def test_parse_price_returns_none_for_invalid_values(value: str) -> None:
    assert parse_price(value) is None
