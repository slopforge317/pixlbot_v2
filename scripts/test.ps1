$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $projectRoot ".env.test.example"

$previousPostgresPassword = $env:POSTGRES_PASSWORD
$previousPostgresDatabase = $env:POSTGRES_DB
$previousPostgresPort = $env:POSTGRES_PORT
$previousBotToken = $env:BOT_TOKEN
$previousWebhookSecret = $env:WEBHOOK_SECRET
$previousKieCallbackSecret = $env:KIE_CALLBACK_SECRET

$env:POSTGRES_PASSWORD = "pixlbot_test"
$env:POSTGRES_DB = "pixlbot_test"
$env:POSTGRES_PORT = "5433"
$env:BOT_TOKEN = "1234567890:pytest-placeholder-token"
$env:WEBHOOK_SECRET = "pytest-webhook-secret"
$env:KIE_CALLBACK_SECRET = "pytest-kie-callback-secret"

$composeArgs = @(
    "compose",
    "--project-name", "pixlbot-pytest",
    "--env-file", $envFile,
    "-f", (Join-Path $projectRoot "compose.test.yaml")
)

try {
    docker @composeArgs up -d postgres
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to start the test PostgreSQL service."
    }

    docker @composeArgs exec -T postgres sh -c "dropdb --if-exists -U pixlbot pixlbot_pytest && createdb -U pixlbot pixlbot_pytest"
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to recreate the isolated pixlbot_pytest database."
    }

    $env:TEST_DATABASE_URL = "postgresql+asyncpg://pixlbot:pixlbot_test@localhost:5433/pixlbot_pytest"
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
}
finally {
    $env:POSTGRES_PASSWORD = $previousPostgresPassword
    $env:POSTGRES_DB = $previousPostgresDatabase
    $env:POSTGRES_PORT = $previousPostgresPort
    $env:BOT_TOKEN = $previousBotToken
    $env:WEBHOOK_SECRET = $previousWebhookSecret
    $env:KIE_CALLBACK_SECRET = $previousKieCallbackSecret
}
