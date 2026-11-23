# Restore the synthetic demo dataset (wipes local JSON data and uploads)
$root = Split-Path -Parent $PSScriptRoot
Set-Location (Join-Path $root "backend")
.\.venv\Scripts\python -m scripts.reset_demo_data
