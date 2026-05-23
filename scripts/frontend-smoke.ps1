$ErrorActionPreference = "Stop"

$python = ".\.venv\Scripts\python.exe"
$baseUrl = "http://127.0.0.1:8766"

if (-not (Test-Path $python)) {
  throw "Virtual environment is missing. Run setup from README.md first."
}

try {
  Invoke-WebRequest -UseBasicParsing "$baseUrl/api/goal" -TimeoutSec 5 | Out-Null
} catch {
  throw "Web app is not running at $baseUrl. Start it with: .\scripts\web.ps1"
}

& $python .\scripts\frontend_smoke.py --base-url $baseUrl
