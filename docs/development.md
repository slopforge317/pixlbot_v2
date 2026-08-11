# Разработка и проверки

## Требования

- Docker с Docker Compose.
- Python 3.12 или 3.13 и Poetry 2.
- Node.js 24.18 и pnpm 11.

## Установка локальных зависимостей

```powershell
.\scripts\setup.ps1
```

Скрипт создаёт `.env.test` из `.env.test.example`, если файла ещё нет, и
устанавливает зависимости backend и нового TMA. Реальные секреты не нужны для
статических проверок.

## Статические проверки

```powershell
.\scripts\check.ps1
```

Проверяются Poetry, Black, isort, flake8, pyright, TypeScript, production build
нового TMA и итоговая `compose.test.yaml` конфигурация.

## Backend tests

```powershell
.\scripts\test.ps1
```

Скрипт поднимает отдельный Compose project `pixlbot-pytest`, публикует PostgreSQL
только на `127.0.0.1:5433`, создаёт базу `pixlbot_pytest` и запускает pytest.
Серверная `.env.test` и серверный PostgreSQL volume при этом не используются.

## Seed

Seed обновляет providers, models, pricing variants и packages. На восстановленной
legacy-БД запускайте его только после migrations, `alembic check` и summary:

```powershell
.\scripts\seed.ps1
```

Серверный порядок действий описан в `docs/deployment.md`.

Модели хранятся по одному файлу в `apps/backend/catalog/models`. Правила
добавления, валидации, просмотра diff и применения описаны в
`apps/backend/docs/model-catalog.md`.
