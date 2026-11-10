"""Fetch and persist public IBGE/SIDRA indicators for market analysis."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"

SIDRA_URL = "https://apisidra.ibge.gov.br/values"
TIMEOUT_SECONDS = 30


def sidra_query(
    table: str, variable: str, period: str, extra: str = ""
) -> list[dict[str, Any]]:
    """Query SIDRA and return validated rows as dictionaries."""
    suffix = f"/{extra}" if extra else ""
    url = f"{SIDRA_URL}/t/{table}/n3/all/v/{variable}/p/{period}{suffix}"
    response = requests.get(url, timeout=TIMEOUT_SECONDS)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, list) or len(payload) < 2:
        raise ValueError(f"Unexpected SIDRA response for URL: {url}")
    return payload


def save_json(path: Path, payload: Any) -> None:
    """Write a JSON payload using UTF-8 and stable indentation."""
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def fetch_indicators(output_dir: Path = DATA_DIR, period: str = "2024") -> None:
    """Fetch population and income indicators into ``output_dir``."""
    output_dir.mkdir(parents=True, exist_ok=True)
    population = sidra_query("6579", "9324", period)
    income = sidra_query("7531", "10824", period, "c1019/49243")

    save_json(output_dir / "ibge_state_population.json", population)
    save_json(output_dir / "ibge_state_income.json", income)

    population_df = pd.DataFrame(population[1:])
    income_df = pd.DataFrame(income[1:])
    population_df.to_csv(output_dir / "ibge_state_population.csv", index=False)
    income_df.to_csv(output_dir / "ibge_state_income.csv", index=False)

    print(f"IBGE data saved to: {output_dir}")


def main() -> None:
    """Run the default 2024 IBGE collection."""
    fetch_indicators()


if __name__ == "__main__":
    main()
