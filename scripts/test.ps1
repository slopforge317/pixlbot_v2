$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $projectRoot ".env"
if (-not (Test-Path -LiteralPath $envFile)) {
    $envFile = Join-Path $projectRoot ".env.example"
}

$composeArgs = @(
    "compose",
    "--env-file", $envFile,
    "-f", (Join-Path $projectRoot "compose.yaml"),
    "-f", (Join-Path $projectRoot "compose.test.yaml")
)

docker @composeArgs up -d postgres
if ($LASTEXITCODE -ne 0) {
    throw "Unable to start the test PostgreSQL service."
}

$testPort = if ($env:TEST_POSTGRES_PORT) { $env:TEST_POSTGRES_PORT } else { "5433" }
$env:TEST_DATABASE_URL = "postgresql+asyncpg://pixlbot:pixlbot_test@localhost:$testPort/pixlbot_test"
$env:PYTHONPATH = "app"

Push-Location (Join-Path $projectRoot "apps/backend")
try {
    poetry run pytest -q
    if ($LASTEXITCODE -ne 0) {
        throw "Backend tests failed with exit code $LASTEXITCODE"
    }
}
finally {
    Pop-Location
}
