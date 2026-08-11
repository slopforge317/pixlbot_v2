# Каталог моделей

Каталог хранится в `apps/backend/catalog/models`. Один YAML-файл — одна
публичная модель в TMA. Внутри находятся её KIE-реализации, параметры и цены.

Например, `gpt-image-2.yaml` содержит две реализации:

- `text_only` — используется без референсов;
- `image_required` — используется, когда добавлено хотя бы одно фото.

Пользователь видит только общий `title`. Внутренний `title` реализации в
селекторе не показывается.

## Добавить модель

1. Скопировать ближайший YAML в `catalog/models/<slug>.yaml`.
2. Из документации провайдера заполнить точные `api_model_id`, параметры,
   ограничения и `input_mode`.
3. Задать `sort_order` шагом 10.
4. Параметры, влияющие на цену, отметить `variant: true`.
5. Для каждой комбинации таких параметров добавить строку `pricing`.
6. Проверить каталог и посмотреть итоговый YAML:

```powershell
poetry run python scripts/model_catalog.py validate
poetry run python scripts/model_catalog.py show gpt-image-2
```

## Команды управления

Запускаются из `apps/backend`:

```powershell
poetry run python scripts/model_catalog.py validate
poetry run python scripts/model_catalog.py list
poetry run python scripts/model_catalog.py show <slug>
poetry run python scripts/model_catalog.py diff
poetry run python scripts/model_catalog.py seed
```

- `validate` не обращается к БД и проверяет структуру, уникальность slug/API ID,
  режимы входа, лимиты изображений и соответствие pricing variants.
- `diff` только читает БД и показывает, что изменит seed.
- `seed` выполняет идемпотентное применение каталога.

Файл каталога является источником истины. Модели и providers, удалённые из
каталога, не удаляются из БД ради истории генераций, но seed деактивирует их.
Удалённые варианты цены тоже деактивируются.

## GPT Image 2

- публичное название: `GPT Image 2`;
- API ID: `gpt-image-2-text-to-image` и
  `gpt-image-2-image-to-image`;
- prompt: до 20 000 символов;
- референсы: до 16 файлов, каждый до 30 MB;
- качество: только 2K и 4K;
- цена: 2K — 3 кредита, 4K — 4 кредита для обоих режимов.

Поскольку провайдер не поддерживает часть соотношений сторон в 2K/4K, эти
варианты в TMA не выдаются.

## Сервер test

Сначала проверить новый каталог без изменения БД:

```bash
docker compose --env-file .env.test -f compose.test.yaml --profile tools \
  run --rm seed python scripts/model_catalog.py validate

docker compose --env-file .env.test -f compose.test.yaml --profile tools \
  run --rm seed python scripts/model_catalog.py diff
```

Затем применить полный seed моделей и пакетов:

```bash
docker compose --env-file .env.test -f compose.test.yaml --profile tools \
  run --rm seed
```
