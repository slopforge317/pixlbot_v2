$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $projectRoot ".env.test"
$envExamplePath = Join-Path $projectRoot ".env.test.example"

if (-not (Test-Path -LiteralPath $envPath)) {
    Copy-Item -LiteralPath $envExamplePath -Destination $envPath
    Write-Output "Created .env.test from .env.test.example. Replace placeholder secrets before deployment."
}

Push-Location (Join-Path $projectRoot "apps/backend")
try {
    poetry install --no-root
}
finally {
    Pop-Location
}

pnpm --dir (Join-Path $projectRoot "apps/tma") install --frozen-lockfile

Write-Output "Local dependencies are installed."
