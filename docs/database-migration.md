# Миграции legacy-БД

## Цепочка Alembic

Новая история начинается со squashed baseline, revision которой совпадает с
revision в legacy dump:

```text
f7d735a7befd  legacy baseline
      ↓
20260805_0001  native PostgreSQL enums → VARCHAR
      ↓
20260811_0001  model catalog slug/input mode
      ↓
будущие миграции
```

`f7d735a7befd_legacy_baseline.py` создаёт полную legacy-схему на чистой БД. Она
использует те же три native PostgreSQL enum, которые находятся в dump.

`20260805_0001_normalize_legacy_enums.py` переводит их в типы текущей ORM-схемы:

- `funnel_steps.trigger_event` → `VARCHAR(21)`;
- `funnel_steps.condition` → `VARCHAR(18)`;
- `scheduled_messages.status` → `VARCHAR(9)`.

`20260811_0001_add_model_catalog_fields.py` добавляет стабильные slug каталогов,
режим входных данных внутренних моделей и деактивирует video providers/models.
Видео-строки сохраняются для существующей истории генераций.

## Восстановленная база

В dump уже находится `alembic_version = f7d735a7befd`. Поэтому после
`pg_restore` Alembic считает baseline выполненной и применяет только миграции,
идущие после неё:

```bash
docker compose --env-file .env.test -f compose.test.yaml run --rm migrate
```

Ручной `stamp`, подмена revision и отдельный adoption не требуются.

После upgrade обязательно проверить соответствие схемы ORM metadata:

```bash
docker compose \
  --env-file .env.test \
  -f compose.test.yaml \
  run --rm migrate python -m alembic check
```

Если `alembic check` на восстановленном dump обнаружит дополнительные отличия,
backend не запускают. Отличия оформляются новой Alembic migration и сначала
проверяются на новой копии dump.

## Чистая база

На чистом PostgreSQL `alembic upgrade head` последовательно создаёт legacy
baseline, нормализует enum и применяет все последующие revision. Поэтому схема
остаётся воспроизводимой без dump; пользовательских данных в ней не будет.

## Следующие изменения

Каждое изменение SQLAlchemy-моделей сопровождается новой migration с
`down_revision`, указывающей на текущий head. До commit выполняются:

```powershell
cd apps/backend
$env:PYTHONPATH = "app"
poetry run alembic revision --autogenerate -m "describe change"
poetry run alembic upgrade head
poetry run alembic check
```

Сгенерированную migration необходимо проверить вручную. Преобразования данных,
без которых новая версия приложения не работает, размещаются в `upgrade()`, а не
в seed.

## Данные и backup

- Реальные пользователи и операции восстанавливаются только через `pg_restore`.
- Dump и секреты не хранятся в Git.
- Перед каждой migration на рабочей БД создаётся новый custom-format backup и
  checksum.
- `seed` используется только для управляемого обновления каталога моделей и цен.
- `docker compose down -v` удаляет постоянную БД и запрещён для рабочего стенда.
