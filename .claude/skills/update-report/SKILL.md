---
name: update-report
description: Change the Portuguese course report (text, tables, figures, equations, references) and verify it the way a reader sees it. Use for any edit to src/generate_report_docx.py, docx_builder.py, omml.py, strategic_analysis.py or the report figures.
---

# Update the report

1. **Edit the source, never the output.** The `.docx` is generated. Make small changes with Edit. For a change
   that touches several places, write a script with the Write tool: assert that every replacement matches exactly
   once and write all files only at the end.
2. **Do not type numbers.** Cite tables, figures and sections with `R('label')` and `num('label')`. A new target
   that other text cites goes in `LABEL_MAP`.
3. **Follow the writing rules** in `CLAUDE.md`: no dash, self-explanatory titles, no process words, public sources
   only, references contiguous and every one cited.
4. **Run the tests**: `python -m pytest -q`. They check structure, numbering, citations, equations, dashes, figure
   scale and cross-references.
5. **Build the PDF**: `powershell scripts/build_report_pdf.ps1`.
6. **Look at it**: `python scripts/report_check.py --png "<caption of each changed table or figure>"`, then open the
   PNGs. Check: page count and where the conclusion falls, empty bands over 90 pt, a header alone at a page
   bottom, text too small, a table column that breaks words.
7. **Fix and repeat** from step 4 until the pages look right. Report the result with the facts: pages, what you
   viewed, what you could not check.
8. Commit with the `ship` skill. The PDF is not committed.
