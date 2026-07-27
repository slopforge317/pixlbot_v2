# Локальная разработка

## Требования

- Docker Desktop с Docker Compose.
- Python 3.12 и Poetry 2.
- Node.js 24.18 и pnpm 11.

## Первичная настройка

```powershell
.\scripts\setup.ps1
```

После создания `.env` замените значения `BOT_TOKEN`, `POSTGRES_PASSWORD`,
`WEBHOOK_SECRET` и `KIE_CALLBACK_SECRET`.

## Запуск

```powershell
.\scripts\dev.ps1
```

- TMA: `http://localhost:5173`
- Backend: `http://localhost:8000`
- Health check: `http://localhost:8000/health`

## Seed

```powershell
.\scripts\seed.ps1
```

## Monitoring

```powershell
docker compose `
  --env-file .env `
  -f compose.yaml `
  -f compose.dev.yaml `
  -f compose.monitoring.yaml `
  --profile monitoring `
  up -d
```

- Grafana: `http://localhost:3000`
- Prometheus: `http://localhost:9090`
- Loki: `http://localhost:3100`

## Проверки

```powershell
.\scripts\check.ps1
.\scripts\test.ps1
```

`check.ps1` выполняет статические проверки, frontend build и проверку Compose.
`test.ps1` поднимает отдельный PostgreSQL на порту 5433 и запускает backend tests.
