# Regenerate the article PDF from the live page, using the print stylesheet
# that lives in llm-weight-edit-interpretability/index.html (@media print).
#
#   pwsh -File make_pdf.ps1
#
# Needs Microsoft Edge (headless). The result is committed next to the post as
# paper.pdf and served at /blog/llm-weight-edit-interpretability/paper.pdf.

$edge = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
$url  = "https://veolyn-ai.github.io/blog/llm-weight-edit-interpretability/"
$out  = Join-Path $PSScriptRoot "llm-weight-edit-interpretability\paper.pdf"

if (-not (Test-Path $edge)) { throw "Edge not found at $edge" }

& $edge --headless=new --disable-gpu `
        --window-size=794,1123 `
        --no-pdf-header-footer `
        --run-all-compositor-stages-before-draw `
        --virtual-time-budget=15000 `
        --print-to-pdf="$out" $url

Write-Host "wrote $out"
