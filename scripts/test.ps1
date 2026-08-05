$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $projectRoot ".env.test.example"

$previousPostgresPassword = $env:POSTGRES_PASSWORD
$previousPostgresDatabase = $env:POSTGRES_DB
$previousPostgresPort = $env:POSTGRES_PORT
$previousPostgresVolumeName = $env:POSTGRES_VOLUME_NAME
$previousBotToken = $env:BOT_TOKEN
$previousWebhookSecret = $env:WEBHOOK_SECRET
$previousKieCallbackSecret = $env:KIE_CALLBACK_SECRET
$previousDatabaseUrl = $env:DATABASE_URL
$previousTestDatabaseUrl = $env:TEST_DATABASE_URL
$previousPythonPath = $env:PYTHONPATH

$env:POSTGRES_PASSWORD = "pixlbot_test"
$env:POSTGRES_DB = "pixlbot_test"
$env:POSTGRES_PORT = "5433"
$env:POSTGRES_VOLUME_NAME = "pixlbot_pytest_postgres_data"
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

    docker @composeArgs exec -T postgres dropdb --if-exists -U pixlbot pixlbot_pytest
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to drop the isolated pixlbot_pytest database."
    }
    docker @composeArgs exec -T postgres createdb -U pixlbot pixlbot_pytest
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to create the isolated pixlbot_pytest database."
    }

    docker @composeArgs exec -T postgres dropdb --if-exists -U pixlbot pixlbot_migration_test
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to drop the isolated migration database."
    }
    docker @composeArgs exec -T postgres createdb -U pixlbot pixlbot_migration_test
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to create the isolated migration database."
    }

    $env:PYTHONPATH = "app"

    Push-Location (Join-Path $projectRoot "apps/backend")
    try {
        $env:DATABASE_URL = "postgresql+asyncpg://pixlbot:pixlbot_test@localhost:5433/pixlbot_migration_test"
        poetry run alembic upgrade f7d735a7befd
        if ($LASTEXITCODE -ne 0) {
            throw "Legacy baseline migration failed with exit code $LASTEXITCODE"
        }
        poetry run alembic upgrade head
        if ($LASTEXITCODE -ne 0) {
            throw "Migration to head failed with exit code $LASTEXITCODE"
        }
        poetry run alembic check
        if ($LASTEXITCODE -ne 0) {
            throw "Alembic schema check failed with exit code $LASTEXITCODE"
        }

        $env:TEST_DATABASE_URL = "postgresql+asyncpg://pixlbot:pixlbot_test@localhost:5433/pixlbot_pytest"
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
    $env:POSTGRES_VOLUME_NAME = $previousPostgresVolumeName
    $env:BOT_TOKEN = $previousBotToken
    $env:WEBHOOK_SECRET = $previousWebhookSecret
    $env:KIE_CALLBACK_SECRET = $previousKieCallbackSecret
    $env:DATABASE_URL = $previousDatabaseUrl
    $env:TEST_DATABASE_URL = $previousTestDatabaseUrl
    $env:PYTHONPATH = $previousPythonPath
}
