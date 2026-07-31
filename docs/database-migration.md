# Принятие legacy-БД

## Почему требуется adoption

Legacy-БД была создана через SQLAlchemy `create_all`. Её Alembic history содержит
пустую initial revision и последующую revision `f7d735a7befd`. Новый репозиторий
имеет воспроизводимую initial migration `20260727_0001`, которая создаёт всю схему
на чистой PostgreSQL.

Запуск новой initial migration поверх восстановленной legacy-БД попытался бы
повторно создать существующие таблицы. Поэтому новая baseline принимается через
явную операцию, но только после проверки совместимости схемы.

## Инструмент

`apps/backend/scripts/adopt_legacy_schema.py` поддерживает команды:

- `check` — проверяет старую revision и сравнивает БД с ORM metadata;
- `reconcile-enums` — транзакционно переводит три legacy native enums в `VARCHAR`;
- `adopt` — заменяет revision на `20260727_0001`, только если diff пуст;
- `sanitize` — отменяет pending messages и отключает funnel steps в test-копии;
- `summary` — показывает revision и количество строк в основных таблицах.

Изменяющие команды требуют точных confirmation values. Они не запускаются
автоматически вместе с backend.

Legacy enum reconciliation затрагивает:

- `funnel_steps.trigger_event`;
- `funnel_steps.condition`;
- `scheduled_messages.status`.

Если после преобразования остаётся любой другой schema diff, транзакция
откатывается и adoption запрещается.

## Правила безопасности

1. Работать только с восстановленной копией в `pixlbot-next-test`.
2. До adoption иметь проверенный dump и checksum вне сервера.
3. Не выполнять `alembic stamp` вручную.
4. Не продолжать при непустом schema diff.
5. Не запускать backend до sanitization фоновых сообщений.
6. Сравнить summary с исходной БД до seed.
7. Не использовать `docker compose down -v`.
