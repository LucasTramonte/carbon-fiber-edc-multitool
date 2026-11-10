"""Coleta indicadores estaduais do IBGE/SIDRA para a análise de mercado."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "dados"
DATA_DIR.mkdir(exist_ok=True)

SIDRA_URL = "https://apisidra.ibge.gov.br/values"
TIMEOUT_SECONDS = 30


def sidra_query(table: str, variable: str, period: str, extra: str = "") -> list[dict[str, Any]]:
    """Consulta uma tabela SIDRA e retorna as linhas em formato de dicionário."""
    suffix = f"/{extra}" if extra else ""
    url = f"{SIDRA_URL}/t/{table}/n3/all/v/{variable}/p/{period}{suffix}"
    response = requests.get(url, timeout=TIMEOUT_SECONDS)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, list) or len(payload) < 2:
        raise ValueError(f"Resposta SIDRA inesperada para a URL: {url}")
    return payload


def save_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    period = "2024"
    population = sidra_query("6579", "9324", period)
    income = sidra_query("7531", "10824", period, "c1019/49243")

    save_json(DATA_DIR / "ibge_populacao_estados.json", population)
    save_json(DATA_DIR / "ibge_renda_estados.json", income)

    population_df = pd.DataFrame(population[1:])
    income_df = pd.DataFrame(income[1:])
    population_df.to_csv(DATA_DIR / "ibge_populacao_estados.csv", index=False)
    income_df.to_csv(DATA_DIR / "ibge_renda_estados.csv", index=False)

    print(f"Dados do IBGE salvos em: {DATA_DIR}")


if __name__ == "__main__":
    main()
