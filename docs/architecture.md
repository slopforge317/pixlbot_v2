# Архитектура

## Компоненты

```text
Telegram Mini App
       |
       v
Nginx / Vite dev proxy
       |
       v
FastAPI API ---- PostgreSQL
       |
       +---- Telegram Bot API
       +---- KIE API
       +---- S3-compatible storage
       +---- YooKassa
```

- `apps/backend` содержит HTTP API, Telegram bot и текущие фоновые циклы.
- `apps/tma` является целевым пользовательским интерфейсом.
- `apps/tma-legacy` хранится только для переноса существующих сценариев.
- `infra/monitoring` подключается через `compose.monitoring.yaml`. Grafana Alloy
  собирает Docker logs и отправляет их в Loki; Prometheus получает системные и
  PostgreSQL metrics.

## Текущие ограничения

- Генерации запускаются через FastAPI `BackgroundTasks` и пока не являются
  устойчивой очередью.
- Telegram polling и периодические задачи работают в процессе API, поэтому
  backend нельзя безопасно масштабировать несколькими экземплярами.
- Grafana PostgreSQL datasource пока использует application database user.
  Перед production нужен отдельный read-only пользователь.

Эти ограничения не блокируют локальную разработку, но должны быть устранены до
горизонтального масштабирования production.
