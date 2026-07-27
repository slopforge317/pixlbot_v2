$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $projectRoot ".env"

if (-not (Test-Path -LiteralPath $envFile)) {
    throw "Missing .env. Run .\scripts\setup.ps1 and replace placeholder secrets first."
}

docker compose `
    --env-file $envFile `
    -f (Join-Path $projectRoot "compose.yaml") `
    -f (Join-Path $projectRoot "compose.dev.yaml") `
    up --build
