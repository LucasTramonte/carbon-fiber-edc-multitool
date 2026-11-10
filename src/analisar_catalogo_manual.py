"""Analisa observacoes manuais de produtos comparaveis."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd


REQUIRED_COLUMNS = {
    "fonte",
    "url",
    "termo_busca",
    "data_hora_coleta",
    "titulo",
    "preco_exibido",
    "moeda",
    "material",
    "funcoes",
    "dimensoes",
    "peso",
    "avaliacoes",
    "disponibilidade",
    "frete",
    "vendedor_fabricante",
    "observacoes",
    "evidencia_arquivo",
}


def parse_price(value: object) -> float | None:
    if pd.isna(value):
        return None
    text = str(value).strip().replace("R$", "").replace(" ", "")
    if not text or text.lower() in {"não informado", "nao informado", "n/a"}:
        return None
    text = re.sub(r"[^\d,.-]", "", text)
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def load_observations(path: Path) -> pd.DataFrame:
    data = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    missing = sorted(REQUIRED_COLUMNS - set(data.columns))
    if missing:
        raise ValueError(f"Colunas ausentes: {', '.join(missing)}")
    if "categoria" not in data.columns:
        data["categoria"] = ""
    data["preco_brl_num"] = data["preco_exibido"].map(parse_price)
    data["url"] = data["url"].str.strip()
    data["titulo"] = data["titulo"].str.strip()
    valid = data[
        data["url"].ne("")
        & data["titulo"].ne("")
        & data["preco_brl_num"].notna()
        & data["categoria"].ne("")
    ].copy()
    valid = valid.drop_duplicates(subset=["url"], keep="first")
    return valid


def write_outputs(data: pd.DataFrame, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    if data.empty:
        raise ValueError(
            "Nenhuma observacao valida. Preencha titulo, categoria, URL e preco_exibido."
        )

    grouped = data.groupby("categoria")["preco_brl_num"]
    summary = grouped.agg(
        n="count",
        minimo="min",
        q1=lambda values: values.quantile(0.25),
        mediana="median",
        q3=lambda values: values.quantile(0.75),
        maximo="max",
    ).reset_index()
    summary.to_csv(output_dir / "resumo_por_categoria.csv", index=False, encoding="utf-8-sig")

    by_source = data.groupby("fonte").agg(
        n=("preco_brl_num", "count"),
        mediana_brl=("preco_brl_num", "median"),
        minimo_brl=("preco_brl_num", "min"),
        maximo_brl=("preco_brl_num", "max"),
    ).reset_index()
    by_source.to_csv(output_dir / "resumo_por_fonte.csv", index=False, encoding="utf-8-sig")

    functions = (
        data.assign(funcao=data["funcoes"].str.lower().str.split(r"[,;/|]"))
        .explode("funcao")
        .assign(funcao=lambda frame: frame["funcao"].str.strip())
    )
    functions = functions[functions["funcao"].ne("")]
    functions["n_observacoes"] = 1
    functions.groupby("funcao", as_index=False)["n_observacoes"].sum().sort_values(
        "n_observacoes", ascending=False
    ).to_csv(output_dir / "funcoes_observadas.csv", index=False, encoding="utf-8-sig")

    data.to_csv(output_dir / "observacoes_validas.csv", index=False, encoding="utf-8-sig")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--entrada", type=Path, required=True)
    parser.add_argument("--saida", type=Path, required=True)
    args = parser.parse_args()
    observations = load_observations(args.entrada)
    write_outputs(observations, args.saida)
    print(f"{len(observations)} observacoes validas analisadas em {args.saida}")


if __name__ == "__main__":
    main()
