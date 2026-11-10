# Analysis outputs

This directory contains generated artifacts, not primary source data.

- `tables/`: derived CSV tables produced by the analysis pipeline.
- `visualizations/`: PNG charts produced from the derived tables.

Regenerate all outputs from the repository root:

```powershell
python src\consolidate_indicators.py
python src\regional_market_analysis.py
```

Outputs are reproducible planning artifacts. Financial values are explicit
hypotheses and must be replaced with validated quotations before decisions.
