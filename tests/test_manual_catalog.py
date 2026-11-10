"""Unit tests for manual catalog normalization and summaries."""

from pathlib import Path

import pandas as pd
import pytest

from src.analyze_manual_catalog import load_observations, parse_price, write_outputs


def observation(**overrides: str) -> dict[str, str]:
    """Build a valid catalog row with optional field overrides."""
    row = {
        "source": "manual",
        "url": "https://example.com/product",
        "search_term": "card multitool",
        "collected_at": "2026-11-03",
        "title": "Compact tool",
        "displayed_price": "R$ 199,90",
        "currency": "BRL",
        "material": "steel",
        "functions": "screwdriver, bottle opener",
        "dimensions": "85 x 54 mm",
        "weight": "50 g",
        "reviews": "10",
        "availability": "in stock",
        "shipping": "standard",
        "seller_or_manufacturer": "Example",
        "notes": "",
        "evidence_file": "capture.png",
        "category": "multitool",
    }
    row.update(overrides)
    return row


def test_parse_price_handles_brazilian_format() -> None:
    assert parse_price("R$ 1.234,56") == 1234.56


def test_load_observations_deduplicates_urls_and_rejects_invalid_rows(
    tmp_path: Path,
) -> None:
    rows = [
        observation(),
        observation(url="https://example.com/product", displayed_price="R$ 220,00"),
        observation(url="", title=""),
        observation(url="https://example.com/free", displayed_price="not provided"),
    ]
    path = tmp_path / "observations.csv"
    pd.DataFrame(rows).to_csv(path, index=False)

    loaded = load_observations(path)

    assert len(loaded) == 1
    assert loaded.iloc[0]["price_brl"] == 199.90


def test_load_observations_requires_schema(tmp_path: Path) -> None:
    path = tmp_path / "invalid.csv"
    pd.DataFrame([{"url": "https://example.com"}]).to_csv(path, index=False)

    with pytest.raises(ValueError, match="Missing columns"):
        load_observations(path)


def test_write_outputs_rejects_empty_data(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="No valid observations"):
        write_outputs(pd.DataFrame(), tmp_path / "outputs")
