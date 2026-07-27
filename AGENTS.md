# Контекст проекта

Это монорепозиторий Telegram-бота, Telegram Mini App и мониторинга.

## Структура

- `apps/backend` — Python 3.12+, FastAPI, aiogram, SQLAlchemy, PostgreSQL.
- `apps/tma` — основной React + TypeScript + Vite frontend, package manager pnpm.
- `apps/tma-legacy` — временный старый frontend; не развивать без отдельной причины.
- `infra/monitoring` — Grafana, Prometheus, Loki, Promtail и exporters.

## Общие правила

1. Команды Git выполняются из корня монорепозитория.
2. Секреты, `.env`, локальные базы, зависимости и build artifacts не коммитятся.
3. Новый пользовательский интерфейс реализуется в `apps/tma`.
4. `apps/tma-legacy` используется только как источник существующего поведения до
   достижения feature parity.
5. Изменения схемы БД оформляются миграциями Alembic.
6. Перед завершением задачи запускаются релевантные проверки из `scripts`.
7. Документация и команды должны соответствовать фактической структуре проекта.
