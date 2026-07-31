$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $projectRoot ".env.test"

if (-not (Test-Path -LiteralPath $envFile)) {
    throw "Missing .env.test. Run .\scripts\setup.ps1 first."
}

docker compose `
    --env-file $envFile `
    -f (Join-Path $projectRoot "compose.test.yaml") `
    --profile tools `
    run --rm seed
