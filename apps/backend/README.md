# Pixlbot backend

FastAPI, aiogram, SQLAlchemy и PostgreSQL-сервис монорепозитория Pixlbot.

Рабочие команды выполняются из корня монорепозитория:

- локальная настройка и проверки — [`../../docs/development.md`](../../docs/development.md);
- test-развертывание на сервере — [`../../docs/deployment.md`](../../docs/deployment.md);
- перенос legacy-базы — [`../../docs/database-migration.md`](../../docs/database-migration.md);
- переменные backend — [`.env.example`](.env.example);
- API-контракт TMA — [`api_docs/tma_api.md`](api_docs/tma_api.md).

Test-стенд использует PostgreSQL, реальный Telegram `initData` и polling тестового
бота. Генерация, storage, платежи и внешние callback отключены до отдельного этапа.
