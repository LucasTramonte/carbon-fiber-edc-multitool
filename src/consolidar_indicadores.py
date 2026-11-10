"""Consolida população e rendimento estaduais do IBGE por macrorregião."""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "dados"

REGIONS = {
    "Norte": ["AC", "AP", "AM", "PA", "RO", "RR", "TO"],
    "Nordeste": ["AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE"],
    "Sudeste": ["ES", "MG", "RJ", "SP"],
    "Sul": ["PR", "RS", "SC"],
    "Centro-Oeste": ["DF", "GO", "MT", "MS"],
}
UF_BY_CODE = {
    "11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA", "16": "AP",
    "17": "TO", "21": "MA", "22": "PI", "23": "CE", "24": "RN", "25": "PB",
    "26": "PE", "27": "AL", "28": "SE", "29": "BA", "31": "MG", "32": "ES",
    "33": "RJ", "35": "SP", "41": "PR", "42": "SC", "43": "RS", "50": "MS",
    "51": "MT", "52": "GO", "53": "DF",
}


def read_indicator(filename: str) -> dict[str, float]:
    with (DATA_DIR / filename).open(encoding="utf-8-sig", newline="") as file:
        rows = csv.DictReader(file)
        return {UF_BY_CODE[row["D1C"]]: float(row["V"]) for row in rows}


def main() -> None:
    population = read_indicator("ibge_populacao_estados.csv")
    income = read_indicator("ibge_renda_estados.csv")
    total_population = sum(population.values())
    output: list[dict[str, object]] = []
    for region, ufs in REGIONS.items():
        region_population = sum(population[uf] for uf in ufs)
        weighted_income = sum(population[uf] * income[uf] for uf in ufs) / region_population
        output.append(
            {
                "regiao": region,
                "populacao_2024": round(region_population),
                "participacao_populacao_percentual": round(
                    region_population / total_population * 100, 1
                ),
                "rendimento_medio_ponderado_reais": round(weighted_income, 2),
                "uf_incluidas": ", ".join(ufs),
            }
        )
    with (DATA_DIR / "indicadores_regiao_2024.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as file:
        writer = csv.DictWriter(file, fieldnames=output[0].keys())
        writer.writeheader()
        writer.writerows(output)
    print(f"Arquivo salvo: {DATA_DIR / 'indicadores_regiao_2024.csv'}")


if __name__ == "__main__":
    main()
