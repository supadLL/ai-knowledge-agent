$ErrorActionPreference = "Stop"

$python = ".\.venv\Scripts\python.exe"
$baseUrl = "http://127.0.0.1:8766"

if (-not (Test-Path $python)) {
  throw "Virtual environment is missing. Run: python -m venv .venv; .\.venv\Scripts\pip.exe install -e ."
}

& $python -m pytest
& $python -m ruff check .
node --check src\ai_knowledge_agent\static\app.js

& $python -m ai_knowledge_agent.cli index .\data\raw
& $python -m ai_knowledge_agent.cli ask "How does the app preserve local data?"
& $python -m ai_knowledge_agent.cli eval --questions .\evals\questions.json

try {
  $goal = Invoke-WebRequest -UseBasicParsing "$baseUrl/api/goal" -TimeoutSec 5
  if ($goal.StatusCode -ne 200) {
    throw "Unexpected /api/goal status: $($goal.StatusCode)"
  }
  Write-Host "Goal endpoint ok: $baseUrl/goal"
} catch {
  Write-Host "Skipped /goal HTTP check because the web server is not running at $baseUrl."
  Write-Host "Start it with: .\scripts\web.ps1"
}
