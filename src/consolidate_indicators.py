"""Aggregate state-level IBGE indicators by Brazilian macroregion."""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"

REGIONS = {
    "North": ["AC", "AP", "AM", "PA", "RO", "RR", "TO"],
    "Northeast": ["AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE"],
    "Southeast": ["ES", "MG", "RJ", "SP"],
    "South": ["PR", "RS", "SC"],
    "Central-West": ["DF", "GO", "MT", "MS"],
}
UF_BY_CODE = {
    "11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA", "16": "AP",
    "17": "TO", "21": "MA", "22": "PI", "23": "CE", "24": "RN", "25": "PB",
    "26": "PE", "27": "AL", "28": "SE", "29": "BA", "31": "MG", "32": "ES",
    "33": "RJ", "35": "SP", "41": "PR", "42": "SC", "43": "RS", "50": "MS",
    "51": "MT", "52": "GO", "53": "DF",
}


def read_indicator(filename: str, data_dir: Path = DATA_DIR) -> dict[str, float]:
    """Read an IBGE CSV and map state codes to numeric values."""
    with (data_dir / filename).open(encoding="utf-8-sig", newline="") as file:
        rows = csv.DictReader(file)
        return {UF_BY_CODE[row["D1C"]]: float(row["V"]) for row in rows}


def consolidate(
    data_dir: Path = DATA_DIR,
    output_path: Path | None = None,
) -> Path:
    """Create a regional indicator CSV and return its path."""
    population = read_indicator("ibge_state_population.csv", data_dir)
    income = read_indicator("ibge_state_income.csv", data_dir)
    if set(population) != set(income) or len(population) != 27:
        raise ValueError("Population and income data must contain the same 27 states.")

    total_population = sum(population.values())
    output: list[dict[str, object]] = []
    for region, states in REGIONS.items():
        region_population = sum(population[state] for state in states)
        weighted_income = sum(
            population[state] * income[state] for state in states
        ) / region_population
        output.append(
            {
                "region": region,
                "population_2024": round(region_population),
                "population_share_percent": round(
                    region_population / total_population * 100, 1
                ),
                "weighted_mean_income_brl": round(weighted_income, 2),
                "included_states": ", ".join(states),
            }
        )

    destination = output_path or data_dir / "regional_indicators_2024.csv"
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=output[0].keys())
        writer.writeheader()
        writer.writerows(output)
    return destination


def main() -> None:
    """Run the default regional consolidation."""
    path = consolidate()
    print(f"Regional indicators saved to: {path}")


if __name__ == "__main__":
    main()
