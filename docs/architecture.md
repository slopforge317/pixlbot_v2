# Архитектура

## Test-стенд

```text
Telegram client / Browser
          |
          | HTTPS
          v
   Caddy + TMA SPA
          |
          | /api, /health, /webhook
          v
      FastAPI API ---- PostgreSQL
          |
          +---- Telegram Bot API (polling)
          +---- KIE API (следующий этап)
          +---- S3 storage (следующий этап)
          +---- YooKassa (следующий этап)
```

- `apps/tma` собирается в Docker image, где Caddy обслуживает статические файлы,
  выполняет SPA fallback, проксирует backend и управляет TLS.
- `apps/backend` содержит HTTP API и Telegram bot. Funnel и payment cleanup
  workers на первом test-стенде отключены переменными окружения.
- PostgreSQL доступен только внутри Compose network и через loopback host port.
- Caddy хранит ACME state и сертификаты в persistent named volumes.
- BotFather-бот использует обычный Telegram API и polling.

## База данных

- Новая чистая БД создаётся initial migration `20260727_0001`.
- Legacy-БД содержит revision `f7d735a7befd` и не может автоматически пройти
  новый migration graph.
- Legacy schema принимается новой baseline только после автоматического сравнения
  фактической схемы с SQLAlchemy metadata.
- Runtime и seed не создают таблицы через `create_all`; production/test schema
  управляется Alembic.

## Текущие ограничения

- Generations используют FastAPI `BackgroundTasks`, а не устойчивую очередь.
- Telegram polling и периодические задачи находятся в процессе API, поэтому
  backend пока запускается в одном экземпляре.
- KIE callback, S3 uploads и payments не проверяются на первом deployment этапе.
- Monitoring не входит в первый запуск test-стенда.
