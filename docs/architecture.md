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
          +---- Cloudflare R2 (user uploads)
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

- Squashed baseline использует legacy revision `f7d735a7befd` и создаёт точную
  старую схему на чистой PostgreSQL.
- Восстановленная legacy-БД автоматически продолжает обычную Alembic-цепочку с
  migration `20260805_0001`, которая нормализует три native enum.
- PostgreSQL хранится в явно именованном volume `pixlbot_v2_postgres_data`, не
  зависящем от имени Compose project.
- Runtime и seed не создают таблицы через `create_all`; production/test schema
  управляется Alembic.

## Текущие ограничения

- Generations используют FastAPI `BackgroundTasks`, а не устойчивую очередь.
- Telegram polling и периодические задачи находятся в процессе API, поэтому
  backend пока запускается в одном экземпляре.
- KIE callback и payments не проверяются на первом deployment этапе.
- Пользовательские изображения загружаются напрямую из TMA в приватный
  Cloudflare R2 bucket через presigned PUT URL. Backend передаёт KIE временные
  presigned GET URL; lifecycle удаляет объекты с prefix `uploads/` через 1 день.
- Monitoring не входит в первый запуск test-стенда.
