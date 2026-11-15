<#
.SYNOPSIS
  Generate the report .docx and convert it to the local PDF with Microsoft Word.

.DESCRIPTION
  1. runs src\generate_report_docx.py (models, figures, report) with the project's Python;
  2. opens outputs\relatorio_cartao_multitool.docx in Word and saves it as
     assets\relatorio_completo_cartao_multitool.docx.pdf.
  Both files are git-ignored on purpose: the repository keeps the code and data, the PDF stays local.
  Afterwards run: python scripts\report_check.py --png "Tabela 9"
#>
param([string]$Python = "")

$root = Split-Path -Parent $PSScriptRoot
if (-not $Python) {
    $venv = Join-Path $root ".venv\Scripts\python.exe"
    $Python = if (Test-Path $venv) { $venv } else { "python" }
}
& $Python (Join-Path $root "src\generate_report_docx.py")
if ($LASTEXITCODE -ne 0) { throw "report generation failed" }

$docx = Join-Path $root "outputs\relatorio_cartao_multitool.docx"
$pdf = Join-Path $root "assets\relatorio_completo_cartao_multitool.docx.pdf"
$word = New-Object -ComObject Word.Application
$word.Visible = $false
try {
    $document = $word.Documents.Open($docx)
    $document.Repaginate()
    Write-Output ("pages: " + $document.ComputeStatistics(2))
    $document.SaveAs2($pdf, 17)   # 17 = wdFormatPDF
    $document.Close($false)
} finally {
    $word.Quit()
}
Write-Output "PDF written to $pdf"
