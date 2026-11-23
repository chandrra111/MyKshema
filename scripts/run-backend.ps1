# Start the MyKshema API on http://localhost:8000 (creates the venv on first run)
$root = Split-Path -Parent $PSScriptRoot
Set-Location (Join-Path $root "backend")
if (-not (Test-Path ".venv")) { python -m venv .venv; .\.venv\Scripts\python -m pip install -r requirements.txt }
.\.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
