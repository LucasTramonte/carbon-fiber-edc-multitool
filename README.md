<div align="center">
  <img src="assets/brand/product-mark.png" alt="Carbon Fiber EDC Multitool product mark" width="220">
  <h1>Carbon Fiber EDC Multitool</h1>
  <p>Evidence-led product development for everyday carry and urban cycling.</p>
</div>

<div align="center">

[![CI](https://github.com/LucasTramonte/carbon-fiber-edc-multitool/actions/workflows/ci.yml/badge.svg)](https://github.com/LucasTramonte/carbon-fiber-edc-multitool/actions/workflows/ci.yml)
[![CodeQL](https://github.com/LucasTramonte/carbon-fiber-edc-multitool/actions/workflows/codeql.yml/badge.svg)](https://github.com/LucasTramonte/carbon-fiber-edc-multitool/actions/workflows/codeql.yml)

</div>

Reproducible product-development study for a compact carbon-fiber card
multitool intended for everyday carry (EDC) and urban cycling.

The repository is organized as a small research and analysis project. It
separates public source data, executable code, tests, and generated outputs so
that each result can be traced to its inputs and reproduced locally.

## Project scope

The current scope covers:

- exploratory regional market analysis;
- public IBGE/SIDRA data collection and transformation;
- explicit planning assumptions for cost, schedule, and break-even analysis;
- a manual competitor-observation validator for future, sanitized datasets;
- reproducible charts for regional income, financial sensitivity, and project
  scheduling.

This is not a sales forecast, a safety certification, a manufacturing drawing,
or evidence of product-market fit. Technical specifications and commercial
assumptions require prototype testing, quotations, and primary research.

## Repository architecture

```text
.
├── assets/brand/               # Public visual identity assets
├── data/                       # Public inputs and raw API extracts
│   ├── README.md               # Provenance and data contracts
│   ├── ibge_state_*.json      # Raw SIDRA responses
│   └── *.csv                  # Tabular extracts and planning inputs
├── outputs/                    # Generated artifacts only
│   ├── README.md
│   ├── tables/
│   └── visualizations/
├── src/                        # Reusable Python modules and CLI entry points
├── tests/                      # Unit, integration, and adversarial tests
│   └── adversarial/
├── Dockerfile
├── requirements.txt
└── .env.example
```

The product mark is included as a visual identity asset and is displayed at
the top of this document. It is kept separate from analysis outputs and data.

## Engineering automation

The repository includes:

- CI on every push and pull request across supported Python versions;
- CodeQL static analysis for Python;
- dependency review on pull requests;
- Dependabot updates for Python packages and GitHub Actions;
- a pull-request checklist covering provenance, privacy, tests, and outputs;
- `CODEOWNERS` and a security policy for maintainership.

These workflows are intentionally restricted to read-only repository access
unless a security-analysis permission is required by CodeQL.

Academic handouts, copyrighted reference documents, editable reports,
credentials, personal data, and private marketplace exports are intentionally
excluded. The repository is designed to remain publishable without exposing
restricted course material.

## Environment setup

Python 3.10 or newer is recommended.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

The same commands can be run with the Python interpreter configured by the
workspace. The project does not require credentials for the public IBGE
pipeline.

## Reproduce the analysis

Run commands from the repository root:

```powershell
python src\collect_data.py
python src\consolidate_indicators.py
python src\regional_market_analysis.py
```

The first command fetches the 2024 IBGE/SIDRA population and income
indicators, saves the raw JSON responses, and writes CSV extracts. The second
creates regional aggregates. The third writes derived tables to
`outputs/tables/` and PNG visualizations to `outputs/visualizations/`.

The marketplace-related scripts are deliberately not part of the public
repository because access may require OAuth credentials and because raw
marketplace material can contain restricted or identifying information.

## Test-driven quality checks

Run the complete test suite:

```powershell
python -m pytest -q
```

The tests cover:

- valid and invalid price parsing;
- missing-column failures;
- duplicate URL removal;
- negative, non-numeric, and empty prices;
- formula-like spreadsheet text treated as inert data;
- incomplete IBGE inputs;
- regional aggregation invariants;
- generated table and visualization contracts.

The `tests/adversarial/` suite intentionally exercises hostile or malformed
inputs before they reach the analysis outputs. New behavior should be
introduced with a failing test first, followed by the smallest implementation
that makes the test pass, and then a full regression run.

## Data governance

Every quantitative dataset should retain:

1. source institution or endpoint;
2. table, variable, or query identifier;
3. reference period;
4. access date;
5. whether the value is observed, derived, assumed, or hypothetical.

Population, income, advertised listings, sales, purchase intent, and market
segmentation hypotheses are different evidence types. This project does not
use population multiplied by income as a demand estimate. Financial scenarios
use clearly labeled planning assumptions and must not be presented as observed
prices, sales, or market share.

See [`data/README.md`](data/README.md) for the public dataset inventory and
data contracts.

## Security and privacy

Never commit:

- `.env` files, access tokens, refresh tokens, client secrets, or passwords;
- personal information or raw participant responses;
- private marketplace exports or screenshots containing account data;
- course handouts, copyrighted reference files, or unpublished reports.

Use `.env.example` only as a list of variable names. Do not paste secrets into
issues, commits, logs, notebooks, or terminal output. The `.gitignore` file
contains explicit protections for local and restricted materials.

## Container usage

Build and run the public collection pipeline:

```powershell
docker build -t carbon-fiber-edc-multitool .
docker run --rm carbon-fiber-edc-multitool
```

## License and attribution

No open-source license is currently granted. Public data remains subject to
the terms of its original providers. Cite IBGE/SIDRA and Cetic.br according to
their official documentation when reusing the datasets or derived results.
