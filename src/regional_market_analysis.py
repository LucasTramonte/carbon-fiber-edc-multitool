"""Build regional market tables and reproducible planning visualizations."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "outputs"
VISUALIZATION_DIR = OUTPUT_DIR / "visualizations"
TABLE_DIR = OUTPUT_DIR / "tables"

UF_BY_CODE = {
    11: "RO", 12: "AC", 13: "AM", 14: "RR", 15: "PA", 16: "AP", 17: "TO",
    21: "MA", 22: "PI", 23: "CE", 24: "RN", 25: "PB", 26: "PE", 27: "AL",
    28: "SE", 29: "BA", 31: "MG", 32: "ES", 33: "RJ", 35: "SP", 41: "PR",
    42: "SC", 43: "RS", 50: "MS", 51: "MT", 52: "GO", 53: "DF",
}
REGION_BY_STATE = {
    state: region
    for region, states in {
        "North": ["AC", "AP", "AM", "PA", "RO", "RR", "TO"],
        "Northeast": ["AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE"],
        "Southeast": ["ES", "MG", "RJ", "SP"],
        "South": ["PR", "RS", "SC"],
        "Central-West": ["DF", "GO", "MT", "MS"],
    }.items()
    for state in states
}


def load_state_indicators(data_dir: Path = DATA_DIR) -> pd.DataFrame:
    """Load, validate, and join the two state-level IBGE datasets."""
    population = pd.read_csv(data_dir / "ibge_state_population.csv")
    income = pd.read_csv(data_dir / "ibge_state_income.csv")
    state = population[["D1C", "V"]].rename(
        columns={"D1C": "state_code", "V": "population"}
    )
    state["population"] = pd.to_numeric(state["population"], errors="raise")
    state = state.merge(
        income[["D1C", "V"]].rename(
            columns={"D1C": "state_code", "V": "income"}
        ),
        on="state_code",
        validate="one_to_one",
    )
    state["income"] = pd.to_numeric(state["income"], errors="raise")
    state["state"] = state["state_code"].astype(int).map(UF_BY_CODE)
    state["region"] = state["state"].map(REGION_BY_STATE)
    if len(state) != 27 or state.isna().any().any():
        raise ValueError("IBGE inputs must contain one complete row for all 27 states.")
    return state


def build_regional_analysis(state: pd.DataFrame) -> pd.DataFrame:
    """Calculate descriptive population and weighted-income regional metrics."""
    total_population = state["population"].sum()
    rows = []
    for region, frame in state.groupby("region", sort=False):
        population = frame["population"].sum()
        rows.append(
            {
                "region": region,
                "population_2024": round(population),
                "population_share_percent": round(
                    population / total_population * 100, 1
                ),
                "weighted_mean_income_brl": round(
                    np.average(frame["income"], weights=frame["population"]), 2
                ),
                "included_states": ", ".join(sorted(frame["state"])),
            }
        )
    return pd.DataFrame(rows)


def build_financial_sensitivity() -> pd.DataFrame:
    """Build explicitly hypothetical contribution-margin scenarios."""
    frame = pd.DataFrame(
        {"net_price_brl": [149, 199, 249], "hypothetical_variable_cost_brl": [80] * 3}
    )
    frame["unit_contribution_margin_brl"] = (
        frame["net_price_brl"] - frame["hypothetical_variable_cost_brl"]
    )
    frame["break_even_units_54000"] = np.ceil(
        54000 / frame["unit_contribution_margin_brl"]
    ).astype(int)
    frame["break_even_units_60000"] = np.ceil(
        60000 / frame["unit_contribution_margin_brl"]
    ).astype(int)
    return frame


def build_project_schedule() -> pd.DataFrame:
    """Return the planning baseline used by the Gantt visualization."""
    return pd.DataFrame(
        [
            ["A1", "Requirements and primary research", 1, 2, 2, "—", "Team (2)", 2500],
            ["A2", "Functions and morphological matrix", 3, 1, 3, "A1", "Team (2)", 1500],
            ["A3", "CAD, architecture, and tolerances", 4, 2, 5, "A2", "Design (2)", 5000],
            ["A4", "Sheet quotation and procurement", 3, 2, 4, "A1", "Purchasing (1)", 18000],
            ["A5", "Machined prototypes", 6, 2, 7, "A3; A4", "Supplier", 6000],
            ["A6", "Testing and optimization", 8, 2, 9, "A5", "Team (2)", 4500],
            ["A7", "Process, packaging, and inspection", 10, 2, 11, "A6", "Production (2)", 7000],
            ["A8", "Commercial batch preparation", 12, 2, 13, "A7", "Production (2)", 8000],
            ["A9", "Pilot launch and monitoring", 14, 2, 15, "A8", "Marketing (1)", 1500],
            ["A10", "Closeout and lessons learned", 16, 1, 16, "A9", "Team (2)", 0],
        ],
        columns=["id", "activity", "start_week", "duration_weeks", "end_week",
                 "predecessors", "resources", "cost_brl"],
    )


def save_visualizations(regional: pd.DataFrame, financial: pd.DataFrame,
                        schedule: pd.DataFrame, output_dir: Path = VISUALIZATION_DIR) -> None:
    """Render the regional, financial, and schedule PNG outputs."""
    output_dir.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(10, 5.5))
    bars = ax.bar(regional["region"], regional["weighted_mean_income_brl"], color="#263238")
    ax.set(title="Weighted per-capita household income by region (2024)",
           ylabel="BRL per person/month")
    for bar, value in zip(bars, regional["weighted_mean_income_brl"]):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 35,
                f"BRL {value:,.0f}", ha="center", va="bottom", fontsize=9)
    fig.tight_layout()
    fig.savefig(output_dir / "regional_income_2024.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 5.5))
    x = np.arange(len(financial))
    width = 0.36
    ax.bar(x - width / 2, financial["break_even_units_54000"], width,
           label="Planned budget: BRL 54k", color="#37474f")
    ax.bar(x + width / 2, financial["break_even_units_60000"], width,
           label="Budget with reserve: BRL 60k", color="#ef6c00")
    ax.set(title="Units required to recover development budget",
           xlabel="Net selling price per unit (BRL)",
           ylabel="Break-even units")
    ax.set_xticks(x, [f"BRL {value:.0f}" for value in financial["net_price_brl"]])
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_dir / "break_even_sensitivity.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(12, 7.5))
    critical_path = {"A1", "A2", "A3", "A5", "A6", "A7", "A8", "A9", "A10"}
    colors = ["#37474f" if item in critical_path else "#90a4ae"
              for item in schedule["id"]]
    y = np.arange(len(schedule))
    ax.barh(y, schedule["duration_weeks"], left=schedule["start_week"] - 0.5,
            color=colors, edgecolor="#263238", height=0.62)
    ax.set_yticks(y, labels=[f"{item}: {activity}" for item, activity
                             in zip(schedule["id"], schedule["activity"])])
    ax.invert_yaxis()
    ax.set(title="Project planning baseline", xlabel="Project week", ylabel="Activity")
    ax.set_xticks(np.arange(1, 17))
    ax.grid(axis="x", alpha=0.3)
    fig.subplots_adjust(left=0.36, right=0.98, top=0.9, bottom=0.12)
    fig.savefig(output_dir / "project_schedule_gantt.png", dpi=180)
    plt.close(fig)


def run_analysis(data_dir: Path = DATA_DIR, output_dir: Path = OUTPUT_DIR) -> None:
    """Run all regional, financial, and schedule analysis outputs."""
    regional = build_regional_analysis(load_state_indicators(data_dir))
    financial = build_financial_sensitivity()
    schedule = build_project_schedule()
    table_dir = output_dir / "tables"
    table_dir.mkdir(parents=True, exist_ok=True)
    regional.to_csv(table_dir / "regional_market_analysis_2024.csv", index=False)
    financial.to_csv(table_dir / "financial_sensitivity_plan.csv", index=False)
    schedule.to_csv(table_dir / "project_schedule_precedence.csv", index=False)
    save_visualizations(regional, financial, schedule, output_dir / "visualizations")


def main() -> None:
    """Run the default analysis pipeline."""
    run_analysis()
    print(f"Analysis outputs saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
