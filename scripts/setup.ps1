$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $projectRoot ".env"
$envExamplePath = Join-Path $projectRoot ".env.example"

if (-not (Test-Path -LiteralPath $envPath)) {
    Copy-Item -LiteralPath $envExamplePath -Destination $envPath
    Write-Output "Created .env from .env.example. Replace placeholder secrets before starting services."
}

Push-Location (Join-Path $projectRoot "apps/backend")
try {
    poetry install --no-root
}
finally {
    Pop-Location
}

pnpm --dir (Join-Path $projectRoot "apps/tma") install --frozen-lockfile
npm --prefix (Join-Path $projectRoot "apps/tma-legacy") ci

Write-Output "Local dependencies are installed."
