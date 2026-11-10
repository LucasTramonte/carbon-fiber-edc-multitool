"""Validate and summarize manually collected competitor observations."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd

REQUIRED_COLUMNS = {
    "source", "url", "search_term", "collected_at", "title", "displayed_price",
    "currency", "material", "functions", "dimensions", "weight", "reviews",
    "availability", "shipping", "seller_or_manufacturer", "notes",
    "evidence_file",
}
MISSING_PRICE_VALUES = {"", "not informed", "not provided", "n/a", "na"}


def parse_price(value: object) -> float | None:
    """Parse common BRL or numeric price representations safely."""
    if pd.isna(value):
        return None
    text = str(value).strip().lower().replace("r$", "").replace(" ", "")
    if text in MISSING_PRICE_VALUES:
        return None
    text = re.sub(r"[^\d,.-]", "", text)
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    try:
        parsed = float(text)
    except ValueError:
        return None
    return parsed if parsed >= 0 else None


def load_observations(path: Path) -> pd.DataFrame:
    """Load, validate, normalize, and deduplicate catalog observations."""
    data = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    missing = sorted(REQUIRED_COLUMNS - set(data.columns))
    if missing:
        raise ValueError(f"Missing columns: {', '.join(missing)}")
    if "category" not in data.columns:
        data["category"] = ""
    data["price_brl"] = data["displayed_price"].map(parse_price)
    data["url"] = data["url"].str.strip()
    data["title"] = data["title"].str.strip()
    valid = data[
        data["url"].ne("")
        & data["title"].ne("")
        & data["price_brl"].notna()
        & data["category"].str.strip().ne("")
    ].copy()
    return valid.drop_duplicates(subset=["url"], keep="first")


def write_outputs(data: pd.DataFrame, output_dir: Path) -> None:
    """Write category, source, function, and normalized observation tables."""
    if data.empty:
        raise ValueError("No valid observations. Provide URL, title, category, and price.")
    output_dir.mkdir(parents=True, exist_ok=True)
    summary = data.groupby("category")["price_brl"].agg(
        count="count", minimum="min", q1=lambda values: values.quantile(0.25),
        median="median", q3=lambda values: values.quantile(0.75), maximum="max",
    ).reset_index()
    summary.to_csv(output_dir / "summary_by_category.csv", index=False)
    data.groupby("source").agg(
        count=("price_brl", "count"), median_brl=("price_brl", "median"),
        minimum_brl=("price_brl", "min"), maximum_brl=("price_brl", "max"),
    ).reset_index().to_csv(output_dir / "summary_by_source.csv", index=False)
    functions = data.assign(function=data["functions"].str.lower().str.split(r"[,;/|]"))
    functions = functions.explode("function")
    functions["function"] = functions["function"].str.strip()
    functions[functions["function"].ne("")].assign(observation_count=1).groupby(
        "function", as_index=False
    )["observation_count"].sum().sort_values(
        "observation_count", ascending=False
    ).to_csv(output_dir / "observed_functions.csv", index=False)
    data.to_csv(output_dir / "valid_observations.csv", index=False)


def main() -> None:
    """Parse command-line paths and write catalog analysis outputs."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    observations = load_observations(args.input)
    write_outputs(observations, args.output)
    print(f"Analyzed {len(observations)} valid observations in {args.output}")


if __name__ == "__main__":
    main()
