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
  scheduling;
- a project plan model (WBS, critical path, cost by resource type, weekly
  baseline) in the format of the course examples;
- an end-of-life (reverse logistics) planning model with labelled assumptions,
  decision matrices, and scenario tables;
- a strategic environment analysis (SWOT matrix and Porter's five forces) kept
  as data, so the report text, table and figures come from one source;
- a market and technology survey organized by the course typology of sources:
  public statistics (IBGE, Cetic.br), the national cyclist profile survey,
  patents and competing products, with ROI, NPV and IRR goals by sales volume and a
  sample-size and price-research design for the primary research still to do;
- the complete Portuguese course report as DOCX (body under 15 pages plus
  appendices), generated from those models.

This is not a sales forecast, a safety certification, a manufacturing drawing,
or evidence of product-market fit. Technical specifications and commercial
assumptions require prototype testing, quotations, and primary research.

## Workflow at a glance

Two workflows matter here: how the repository turns labelled inputs into the
report, and what happens to a card the customer sends back. The report itself
is written in Portuguese for the course; everything in this README and in
`docs/workflows/` is English.

### 1. From inputs to the report

```mermaid
flowchart LR
    subgraph IN["Inputs"]
        PUB[("Public data<br/>IBGE/SIDRA")]
        ASM[("Labelled assumptions<br/>data/*.csv")]
    end
    PUB --> ANA["regional_market_analysis.py"]
    ASM --> PLAN["project_plan.py<br/>WBS, CPM, costs"]
    ASM --> MOD["reverse_logistics_model.py<br/>scenarios, matrices"]
    ANA --> TAB["Tables and charts<br/>outputs/"]
    PLAN --> TAB
    MOD --> TAB
    STR["strategic_analysis.py<br/>SWOT, five forces"] --> TAB
    PLAN --> DIA["Diagram specs<br/>Mermaid + Graphviz"]
    MOD --> DIA
    DIA --> TAB
    TAB --> DOC["generate_report_docx.py"]
    DOC --> OUT(["Report .docx<br/>under 15 pages + appendices"])
    TST{{"pytest: all pass?"}}
    PLAN -.-> TST
    MOD -.-> TST
    STR -.-> TST
    DOC -.-> TST
    TST -->|"yes"| OUT
    classDef gate fill:#ef6c00,stroke:#263238,color:#fff;
    class TST gate;
```

Change one row of a labelled assumptions file and rerun the commands in
[Reproduce the analysis](#reproduce-the-analysis): numbers, tables, charts, and
the document text update together.

### 2. What happens to a returned card

Where can a returned card go? Only the end-of-life branch is reverse logistics.

<!-- workflow:motivo:start -->
```mermaid
flowchart TD
    inicio(["Card returned<br/>to the seller"])
    why{"Reason<br/>for return?"}
    subgraph lane1["Withdrawal"]
        direction TB
        r1["Re-inspection<br/>(unused card)"]
        r2[("Stock")]
    end
    subgraph lane2["Defect"]
        direction TB
        d1["Failure analysis<br/>tied to engraved lot"]
        d2["Process and<br/>inspection fix"]
    end
    subgraph lane3["End of life"]
        direction TB
        e1["Reverse logistics<br/>(next diagram)"]
    end
    inicio --> why
    why -->|"withdrawal<br/>(within 7 days,<br/>CDC art. 49)"| r1
    why -->|"defect<br/>(warranty,<br/>CDC art. 26)"| d1
    why -->|"end of life<br/>(voluntary)"| e1
    r1 -->|"intact"| r2
    d1 -->|"root cause"| d2
    classDef hot fill:#ef6c00,stroke:#263238,color:#fff;
    class e1 hot;
    classDef term fill:#263238,stroke:#263238,color:#fff;
    class inicio term;
    classDef stock fill:#eceff1,stroke:#263238;
    class r2 stock;
```
<!-- workflow:motivo:end -->

What happens at end of life, and where does the mass end up? Dashed lines are
conditional paths; orange marks the decision point; the cylinder is held stock.
Percentages and kilograms come from the model's reference scenario (assumed
values, not observations).

<!-- workflow:fim_de_vida:start -->
```mermaid
flowchart TD
    e1(["Customer requests return and gets<br/>postage code (company pays,<br/>valid 30 days)"])
    e3["Receipt: log lot, date and mass<br/>(gloves, double bag)"]
    triage["Visual and<br/>dimensional triage"]
    A["A · intact 20%<br/>test piece or<br/>display"]
    B["B · light wear 20%<br/>second life only<br/>if validated"]
    C["C · delaminated 50%<br/>goes to<br/>recycling"]
    D["D · exposed fibre 10%<br/>double bag,<br/>licensed disposal"]
    scrap["Machining offcuts<br/>11.8 kg per lot"]
    stock[("Closed stock per lot<br/>until minimum lot<br/>≈ 15.4 kg per lot")]
    dest["Composite recycler<br/>(acceptance, minimum lot<br/>and price: pending)"]
    voucher["R$ 20 voucher<br/>(1 per validated card)"]
    log["Record: lot, mass,<br/>class and destination"]
    fim(["% received ≥ 10%<br/>or 36 months:<br/>closes the phase"])
    e1 -->|"customer ships<br/>the card"| e3
    e3 --> triage
    triage --> A
    triage --> B
    triage --> C
    triage --> D
    B -.->|"rejected<br/>in test"| C
    C -->|"card"| stock
    D -.->|"card"| stock
    scrap -->|"offcut"| stock
    stock -->|"minimum lot<br/>reached"| dest
    triage -.->|"card validated"| voucher
    dest -->|"certificate"| log
    voucher --> log
    log --> fim
    classDef hot fill:#ef6c00,stroke:#263238,color:#fff;
    class triage hot;
    classDef term fill:#263238,stroke:#263238,color:#fff;
    class e1,fim term;
    classDef stock fill:#eceff1,stroke:#263238;
    class stock stock;
```
<!-- workflow:fim_de_vida:end -->

How the seven discontinuation activities depend on each other (mirrors the
course's phase dependency diagram; D6 also depends directly on the plan):

<!-- workflow:fase:start -->
```mermaid
flowchart LR
    D1["D1 · Analyse and approve<br/>discontinuation"]
    D2["D2 · Plan the<br/>discontinuation"]
    D3["D3 · Prepare<br/>product receipt"]
    D4["D4 · Follow<br/>product receipt"]
    D5["D5 · Stop<br/>production"]
    D6["D6 · End product<br/>support"]
    D7["D7 · Overall review and<br/>project closure"]
    D1 --> D2
    D2 --> D3
    D3 --> D4
    D2 --> D5
    D5 --> D6
    D2 --> D6
    D4 --> D7
    D6 --> D7
```
<!-- workflow:fase:end -->

The diagrams are code, not drawings: one flow specification in
[`src/flow_specs.py`](src/flow_specs.py) (bilingual) is rendered by
[`src/reverse_flow_diagram.py`](src/reverse_flow_diagram.py) into the Mermaid
blocks above (GitHub renders them natively), the English Graphviz sources in
[`docs/workflows/`](docs/workflows/), and the Portuguese PNGs used in the
report. Do not
edit the blocks by hand; run `python src\reverse_flow_diagram.py`.

## Repository architecture

```text
.
├── assets/brand/               # Public visual identity assets
├── docs/workflows/             # Generated Mermaid (.mmd) and Graphviz (.dot) sources
├── report/                     # Cover data template (the real team file is git-ignored)
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

The complete report is reproduced with:

```powershell
python src\generate_report_docx.py        # models, diagrams, figures and the report
                                          #   -> outputs\relatorio_cartao_multitool.docx
python src\reverse_flow_diagram.py        # only the workflow diagrams and README blocks
python src\strategic_analysis.py          # only the SWOT and five-forces figures
                                          #   -> outputs\visualizations\fig_swot.png, fig_porter.png
```

The SWOT items, the five-force scores and their justifications live in
`src/strategic_analysis.py`. The report (Section 1.5) reads them from there, and
the tests check the structure (four quadrants, five forces, scores from 1 to
5), the mean used in the text, and the consistency of the cost figures quoted
in the justifications with the project plan.

Rendering the workflow PNG needs [Graphviz](https://graphviz.org/download/)
(`winget install Graphviz.Graphviz`); without it the model falls back to a
simpler matplotlib drawing. The `.docx` output is ignored by git, like other
report files. Copy `report/team.example.json` to `report/team.local.json` and
fill in the team data to personalise the cover; the local file is git-ignored.

The marketplace-related scripts are deliberately not part of the public
repository because access may require OAuth credentials and because raw
marketplace material can contain restricted or identifying information.

## Economic viability model

The project is evaluated on a weekly cash flow. Development outlays follow the
cost baseline of the schedule; sales start after the development and run at a
constant pace for 12 months. Flows fall at the end of each week, and the
end-of-life cost is proportional to the units sold.

<p align="center">
  <img src="outputs/visualizations/viability_chart_en.png" alt="Cumulative investment, sales and profit by month, with the break-even point" width="760">
</p>

The chart follows the course example: the investment rises during the 14 weeks
of development, sales and profit start at the launch, and the break-even is the
month where the cumulative profit equals the investment (month 9.2 for 1,000
cards; dashed lines show 600 and 2,000 cards).

With $p$ the net unit price, $c_v$ the variable cost, $c_f$ the end-of-life cost
per card, $Q$ the cards sold in 12 months, $C_t$ the cost of week $t$ in the
baseline, $I=\sum_{t=1}^{T_d} C_t$ the investment, $T_d=14$ and $T_v=52$ the weeks
of development and sales ($T=T_d+T_v$), and $i$ the discount rate:

$$m = p - c_v - c_f$$

$$F_t = \begin{cases} -C_t, & 1 \le t \le T_d \\ \dfrac{Q}{T_v}\,m, & T_d < t \le T \end{cases}$$

$$\mathrm{NPV} = \sum_{t=1}^{T} \frac{F_t}{(1+i_s)^t}, \qquad i_s = (1+i)^{1/52} - 1$$

$$\sum_{t=1}^{T} \frac{F_t}{(1+r^*)^t} = 0, \qquad \mathrm{IRR}_{\text{month}} = (1+r^*)^{52/12} - 1$$

$$\mathrm{ROI} = \frac{\sum_{t=1}^{T} F_t}{I} = \frac{Q\,m - I}{I}$$

$$\tau = \min\Big\{k : \sum_{t=1}^{k} F_t \ge 0\Big\}, \qquad \text{payback} = \tau\cdot\tfrac{12}{52}\ \text{months}$$

$$Q_{\mathrm{NPV}=0} = \frac{\sum_{t=1}^{T_d} C_t\,(1+i_s)^{-t}}{\dfrac{m}{T_v}\sum_{t=T_d+1}^{T}(1+i_s)^{-t}}$$

The cash flow changes sign once, so the positive IRR is unique (Descartes' rule
of signs). The simple break-even is $Q_{eq}=\lceil I/m\rceil$, where the ROI is zero.

Parameters: $p=$ R$ 199, $c_v=$ R$ 80 (planning hypotheses), $c_f=$ R$ 11.05
(end-of-life phase cost spread over the 2,000-card lot), $I=$ R$ 54,000, and
$i=13.75\%$ per year, the Selic target published by the Central Bank of Brazil
(SGS series 432), used as the minimum attractive rate.

| Cards sold in 12 months | Break-even (month) | ROI | NPV | Monthly IRR |
| ---: | ---: | ---: | ---: | ---: |
| 600 | 13.2 | 20% | R$ 5,520 | 2.4% |
| 1,000 | 9.2 | 100% | R$ 44,603 | 10.0% |
| 2,000 | 6.2 | 300% | R$ 142,309 | 23.1% |

The simple break-even needs 501 cards and the NPV is positive from 544. These
are planning goals under hypothetical price and cost, not forecasts. The
functions live in `src/project_plan.py` (`cash_flows`, `npv`, `irr_monthly`,
`payback_months`, `economics`, `units_for_zero_npv`) and are covered by tests;
`python src\report_diagrams.py` redraws the chart in Portuguese (for the report)
and in English (for this README).

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
- generated table and visualization contracts;
- the project plan, reverse-logistics and strategic-analysis models, including
  report structure, numbering, citations and table layout.

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

## Team contributions

| Contribution | Where | Author |
| --- | --- | --- |
| SWOT matrix and Porter's five forces (source text and scores) | `src/strategic_analysis.py`, report Section 1.5 | Marco Gabriel Landivar Silva |
| Market analysis, project plan, reverse-logistics model, report generator | `src/`, `data/`, `docs/` | Lucas Tramonte |

The original strategic-analysis document is kept locally as
`assets/SWOT_Porter_cartao_multitool.docx`; like every `.docx`, it is ignored by
git. Its content is versioned here as data and code instead.

## License and attribution

No open-source license is currently granted. Public data remains subject to
the terms of its original providers. Cite IBGE/SIDRA and Cetic.br according to
their official documentation when reusing the datasets or derived results.
