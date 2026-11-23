<#
.SYNOPSIS
  Generate a report .docx and convert it to PDF with Microsoft Word.

.DESCRIPTION
  -Edition pt (default): the Portuguese course report.
     runs src\generate_report_docx.py and saves a DRAFT to outputs\relatorio_cartao_multitool.pdf
     (git-ignored on purpose). The final report, with the CAD drawing and the edits made by hand, is
     assets\relatorio_completo_cartao_multitool.docx.pdf. This script never writes to it, so a rebuild cannot
     overwrite it; to adopt a new final version, copy the file there yourself.
  -Edition en: the English edition linked at the top of the README.
     runs src\generate_report_en.py and saves docs\report\carbon-fiber-edc-multitool-report-en.pdf, which IS
     committed. It also refreshes docs\report\report-en.sha256, the hash of the report text that a test compares
     with the code to catch a PDF that lags behind.
  Afterwards run: python scripts\report_check.py --pdf <the PDF> --png "Table 9"
#>
param(
    [ValidateSet("pt", "en")][string]$Edition = "pt",
    [string]$Python = ""
)

$root = Split-Path -Parent $PSScriptRoot
if (-not $Python) {
    $venv = Join-Path $root ".venv\Scripts\python.exe"
    $Python = if (Test-Path $venv) { $venv } else { "python" }
}
if ($Edition -eq "en") {
    $generator = "src\generate_report_en.py"
    $docx = Join-Path $root "outputs\report_en.docx"
    $pdf = Join-Path $root "docs\report\carbon-fiber-edc-multitool-report-en.pdf"
} else {
    $generator = "src\generate_report_docx.py"
    $docx = Join-Path $root "outputs\relatorio_cartao_multitool.docx"
    $pdf = Join-Path $root "outputs\relatorio_cartao_multitool.pdf"
}
& $Python (Join-Path $root $generator)
if ($LASTEXITCODE -ne 0) { throw "report generation failed" }

$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0   # a hidden dialog (file conflict, sync lock) would hang the conversion
try {
    $document = $word.Documents.Open($docx, $false, $true)   # read-only
    $document.Repaginate()
    Write-Output ("pages: " + $document.ComputeStatistics(2))
    $document.SaveAs2($pdf, 17)   # 17 = wdFormatPDF
    $document.Close($false)
} finally {
    $word.Quit()
}
Write-Output "PDF written to $pdf"
