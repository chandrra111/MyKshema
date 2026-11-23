# Start the MyKshema web app on http://localhost:3000
$root = Split-Path -Parent $PSScriptRoot
Set-Location (Join-Path $root "frontend")
if (-not (Test-Path "node_modules")) { npm install }
npm run dev
