$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$env:BLACK_CACHE_DIR = Join-Path $projectRoot ".tmp/black-cache"

function Invoke-CheckedStep {
    param(
        [Parameter(Mandatory)]
        [string]$Name,
        [Parameter(Mandatory)]
        [scriptblock]$Command
    )

    Write-Output "==> $Name"
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE"
    }
}

Push-Location (Join-Path $projectRoot "apps/backend")
try {
    Invoke-CheckedStep "Poetry configuration" { poetry check }
    Invoke-CheckedStep "Backend formatting" {
        poetry run black --check app tests scripts alembic
    }
    Invoke-CheckedStep "Backend import ordering" {
        poetry run isort --check-only app tests scripts alembic
    }
    Invoke-CheckedStep "Backend lint" {
        poetry run flake8 app tests scripts alembic
    }
    Invoke-CheckedStep "Backend type checking" { poetry run pyright }
}
finally {
    Pop-Location
}

Invoke-CheckedStep "TMA type checking" {
    pnpm --dir (Join-Path $projectRoot "apps/tma") run check
}
Invoke-CheckedStep "TMA production build" {
    pnpm --dir (Join-Path $projectRoot "apps/tma") run build
}

$envFile = Join-Path $projectRoot ".env.test"
if (-not (Test-Path -LiteralPath $envFile)) {
    $envFile = Join-Path $projectRoot ".env.test.example"
}

Invoke-CheckedStep "Test Compose configuration" {
    docker compose --env-file $envFile -f (Join-Path $projectRoot "compose.test.yaml") config --quiet
}

Write-Output "All non-database checks passed."
