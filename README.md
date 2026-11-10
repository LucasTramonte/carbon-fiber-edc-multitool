# Carbon Fiber EDC Multitool

Product development study for a compact carbon-fiber card multitool intended
for everyday carry and urban cycling.

The repository contains reproducible Python scripts, selected public-source
datasets, and planning tables for market analysis and early product
development. Academic course materials, third-party reference documents,
editable reports, credentials, and raw personal data are intentionally
excluded.

## Repository structure

- `src/`: data collection, transformation, and analysis scripts.
- `dados/`: selected datasets and derived tables. File names currently follow
  the source workspace conventions.
- `requirements.txt`: Python dependencies.

## Getting started

Create an isolated Python environment and install the dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Run the public-source data pipeline from the repository root:

```powershell
python src\coletar_dados.py
python src\consolidar_indicadores.py
python src\analise_estatistica_mercado.py
```

The scripts use public IBGE endpoints and save raw responses before producing
derived CSV files. Network requests use explicit timeouts and fail loudly when
an endpoint returns an error.

## Evidence and interpretation

Population, income, advertised prices, sales, purchase intent, and market
hypotheses are treated as different types of evidence. Aggregated population
and income figures are not used as a proxy for product demand. Planning prices,
costs, and break-even scenarios are assumptions for later validation rather
than observed market results.

Each quantitative result should be interpreted together with its source,
table or endpoint, reference period, and access date.

## Data and privacy

Do not commit `.env` files, access tokens, client secrets, passwords, personal
data, course handouts, copyrighted reference material, or unpublished reports.
The included `.env.example` contains variable names only.

## Status

This is an exploratory product development repository. Technical
specifications, manufacturing decisions, cost estimates, and market
assumptions remain subject to prototype testing and primary research.
