#!/usr/bin/env sh
# Start the MyKshema API on http://localhost:8000
cd "$(dirname "$0")/../backend" || exit 1
[ -d .venv ] || { python3 -m venv .venv && .venv/bin/pip install -r requirements.txt; }
.venv/bin/uvicorn app.main:app --reload --port 8000
