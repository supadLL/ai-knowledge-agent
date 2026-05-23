param(
  [string]$OutputRoot = ".\dist",
  [string]$PackageName = "ai-knowledge-agent"
)

$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$outputRootPath = Join-Path $projectRoot $OutputRoot
$packageRoot = Join-Path $outputRootPath $PackageName

New-Item -ItemType Directory -Force -Path $outputRootPath | Out-Null
if (Test-Path $packageRoot) {
  $resolvedOutput = (Resolve-Path $outputRootPath).Path
  $resolvedPackage = (Resolve-Path $packageRoot).Path
  if (-not $resolvedPackage.StartsWith($resolvedOutput, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to clean package path outside output root: $resolvedPackage"
  }
  Remove-Item -LiteralPath $resolvedPackage -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $packageRoot | Out-Null

$directories = @("src", "scripts", "tests", "data\raw", "docs", "evals")
foreach ($directory in $directories) {
  $source = Join-Path $projectRoot $directory
  if (Test-Path $source) {
    $target = Join-Path $packageRoot $directory
    New-Item -ItemType Directory -Force -Path (Split-Path $target -Parent) | Out-Null
    Copy-Item -LiteralPath $source -Destination $target -Recurse -Force
  }
}

$files = @("pyproject.toml", "README.md", ".env.example", "mvp-todo.md")
foreach ($file in $files) {
  Copy-Item -LiteralPath (Join-Path $projectRoot $file) -Destination (Join-Path $packageRoot $file) -Force
}

$launchScript = @'
param(
  [int]$Port = 8766,
  [switch]$SetupOnly
)

$ErrorActionPreference = "Stop"

$root = $PSScriptRoot
$python = Join-Path $root ".venv\Scripts\python.exe"
$pip = Join-Path $root ".venv\Scripts\pip.exe"
Set-Location $root

if (-not (Test-Path $python)) {
  python -m venv (Join-Path $root ".venv")
}

& $python -m pip install --upgrade pip
& $pip install -e $root

if ($SetupOnly) {
  Write-Host "Package environment is ready."
  exit 0
}

Write-Host "Starting AI Knowledge Agent at http://127.0.0.1:$Port"
& $python -m uvicorn ai_knowledge_agent.web:app --host 127.0.0.1 --port $Port
'@
Set-Content -LiteralPath (Join-Path $packageRoot "launch.ps1") -Value $launchScript -Encoding UTF8

$smokeScript = @'
param(
  [int]$Port = 8766
)

$ErrorActionPreference = "Stop"

$root = $PSScriptRoot
$python = Join-Path $root ".venv\Scripts\python.exe"
$pip = Join-Path $root ".venv\Scripts\pip.exe"
Set-Location $root

function Invoke-Step {
  param(
    [scriptblock]$Command
  )
  & $Command
  if ($LASTEXITCODE -ne 0) {
    throw "Command failed with exit code $LASTEXITCODE"
  }
}

& (Join-Path $root "launch.ps1") -SetupOnly -Port $Port
Invoke-Step { & $pip install -e "$root[dev]" }
Invoke-Step { & $python -m pytest }
Invoke-Step { & $python -m ruff check . }
Invoke-Step { node --check (Join-Path $root "src\ai_knowledge_agent\static\app.js") }
Invoke-Step { & $python -m ai_knowledge_agent.cli diagnose }

$process = Start-Process -WindowStyle Hidden -PassThru -FilePath $python -ArgumentList @(
  "-m",
  "uvicorn",
  "ai_knowledge_agent.web:app",
  "--host",
  "127.0.0.1",
  "--port",
  "$Port"
) -WorkingDirectory $root

try {
  Start-Sleep -Seconds 2
  $goal = Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:$Port/api/goal" -TimeoutSec 10
  if ($goal.StatusCode -ne 200) {
    throw "Unexpected /api/goal status: $($goal.StatusCode)"
  }
  Write-Host "Packaged smoke passed: http://127.0.0.1:$Port/goal"
} finally {
  if ($process -and -not $process.HasExited) {
    Stop-Process -Id $process.Id -Force
  }
}
'@
Set-Content -LiteralPath (Join-Path $packageRoot "smoke-packaged.ps1") -Value $smokeScript -Encoding UTF8

Write-Host "Package created: $packageRoot"
Write-Host "Run: powershell -ExecutionPolicy Bypass -File `"$packageRoot\launch.ps1`""
Write-Host "Smoke: powershell -ExecutionPolicy Bypass -File `"$packageRoot\smoke-packaged.ps1`""
