# Assets

Public visual assets used by the repository documentation belong here.

The final Portuguese report PDF (`relatorio_completo_cartao_multitool.docx.pdf`) is the hand-finished
version, with the CAD drawing and 3D model. It is git-ignored and `scripts/build_report_pdf.ps1` never overwrites
it: the script writes its draft to `outputs/`, and a new final version is copied here by hand.

The logo lives under `brand/` as two transparent SVG files (`logo-light.svg` and `logo-dark.svg`), drawn by
`scripts/make_logo.py`; the README shows the one that matches the reader's theme. It is kept separate from data,
analysis outputs and source code. New assets should have a clear source, avoid personal information, and be
checked for embedded metadata before publication.
