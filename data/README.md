# Data directory

This directory stores input datasets used by the public analysis pipeline.

## Provenance

| Dataset | Source | Reference period | Access date |
|---|---|---:|---:|
| `ibge_state_population.*` | IBGE/SIDRA table 6579, variable 9324 | 2024 | 2026-11-03 |
| `ibge_state_income.*` | IBGE/SIDRA table 7531, variable 10824, classification 1019/49243 | 2024 | 2026-11-03 |
| `cetic_online_purchases_by_region_2024.csv` | Cetic.br public research table | 2024 | 2026-11-03 |

The IBGE JSON files preserve the raw API responses. The CSV files are
tabular extracts generated from those responses. `D1C` and `V` are original
SIDRA field names and are retained for traceability.

## Data contracts

- Public-source data must retain its source, reference period, and access date.
- Derived data must be reproducible from a tracked script.
- Population, income, listings, sales, purchase intent, and hypotheses must not
  be presented as interchangeable measures.
- Personal data, credentials, raw marketplace exports, and course materials do
  not belong in this directory.

Derived tables and charts are written to `outputs/`, not mixed with source
inputs.
