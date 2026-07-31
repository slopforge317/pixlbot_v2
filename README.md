# pixlbot

Монорепозиторий Telegram-бота и Telegram Mini App для генерации изображений и видео.

## Компоненты

- `apps/backend` — FastAPI API, Telegram bot, PostgreSQL, payments и generations.
- `apps/tma` — основной React + TypeScript Telegram Mini App.
- `apps/tma-legacy` — временный источник поведения для feature parity.
- `infra/monitoring` — отложенная конфигурация monitoring.

## Текущий deployable baseline

Первый test-стенд разворачивается на `https://tma.pixlbot.ru` через
`compose.test.yaml`. Он включает PostgreSQL, Alembic, backend, обычного
BotFather-бота в polling mode и TMA на Caddy с автоматическим HTTPS.

```bash
cp .env.test.example .env.test
docker compose --env-file .env.test -f compose.test.yaml up -d --build
```

Для восстановленной legacy-БД нельзя сразу выполнять полный запуск. Используйте
пошаговую инструкцию из [docs/deployment.md](docs/deployment.md).

## Локальные проверки

```powershell
.\scripts\setup.ps1
.\scripts\check.ps1
.\scripts\test.ps1
```

## Документация

- [Архитектура](docs/architecture.md)
- [Разработка и проверки](docs/development.md)
- [Развёртывание test-стенда](docs/deployment.md)
- [Принятие legacy-БД](docs/database-migration.md)
