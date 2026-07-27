# Заметки по реализации

## Принятые решения

- Новый монорепозиторий создан в `C:\Users\dev\projects\pixlbot`.
- Старый каталог `C:\Users\dev\projects\bot` остаётся нетронутым источником и
  резервной копией.
- История, ветки и remotes старых вложенных репозиториев не переносятся.
- В новый репозиторий переносится текущее состояние рабочих файлов, включая
  полезные незакоммиченные изменения.
- `apps/tma` является целевым frontend.
- `apps/tma-legacy` переносится временно для проверки feature parity и не должен
  использоваться как основа новой разработки.
- Remote для нового репозитория пока не создаётся.

## Риски и последующие действия

- Реальные `.env.dev` и `.env.test` не будут переноситься автоматически.
- Старые PostgreSQL data directories не переносятся; миграция нужных данных
  потребует отдельного `pg_dump`/restore.
- Alembic initial migration в исходном backend пустая и должна быть заменена
  воспроизводимой начальной схемой до изменения моделей.
- Production Compose из исходного проекта использует устаревшие пути и будет
  пересобран под новую структуру.

## Выполненные этапы

- Создан чистый локальный Git-репозиторий с веткой `main`.
- Добавлены корневые правила исключения секретов, зависимостей и локальных данных.
- Компоненты импортированы отдельными коммитами без вложенной Git-истории.
- Добавлен общий env-контракт и Compose overlays для dev, test и production.
- Новый TMA получил production Dockerfile и Nginx proxy configuration.
- Добавлены PowerShell-команды setup, dev, seed, check и test.

## Отклонения от первоначального плана

- Добавлен отдельный `compose.prod.yaml`. Базовый `compose.yaml` содержит общие
  backend/PostgreSQL сервисы, а frontend определяется окружением. Это позволяет
  dev использовать Vite, а test/production — статическую Nginx-сборку без
  конфликтующих `build` и `image`.
- Monitoring подключён отдельным `compose.monitoring.yaml`.
- Исходный Promtail не перенесён в рабочую конфигурацию: Promtail завершил
  жизненный цикл в марте 2026 года. Docker logs теперь собирает Grafana Alloy.
- Monitoring images закреплены на проверенных release tags. Runtime validation
  остаётся незавершённой до запуска Docker Desktop.
- node-exporter и cAdvisor не включены в первый cross-platform baseline:
  их host mounts ориентированы на Linux и вводили бы в заблуждение при локальной
  работе через Docker Desktop на Windows. На первом этапе остаются PostgreSQL
  business metrics и Docker logs.

## Миграции базы

- Старые Alembic revisions не сохраняются: первая revision была пустой, а вторая
  предполагала, что таблицы уже созданы через SQLAlchemy `create_all`.
- Новый репозиторий получает одну начальную migration, сгенерированную из текущих
  SQLAlchemy models на пустой PostgreSQL.
- Автоматический `create_all` удалён из startup API и standalone bot. Создание и
  обновление production schema выполняется только через Alembic.
- Это решение предполагает новую чистую базу. Перенос существующей production
  базы, если он потребуется, остаётся отдельной задачей.

## Зависимости backend

- `poetry.lock` теперь является отслеживаемым файлом.
- Исходная секция PEP 735 `[dependency-groups]` не распознавалась установленным
  Poetry 2.1.3 как installable group: `pytest` и `pyright` не устанавливались.
- Dev dependencies перенесены в совместимую секцию
  `[tool.poetry.group.dev.dependencies]`.
- Первое разрешение диапазонов установило pytest 9.1.1 и pytest-asyncio 1.4.0.
  В текущем Windows/Python 3.13 окружении тест завершался, но процесс pytest не
  выходил. Для воспроизводимости и проверки исходного baseline версии закреплены
  на исходных минимальных значениях 9.0.2 и 1.3.0.
- Позже установлено, что незавершение процесса было следствием запрета sandbox на
  запись pytest cache в соседний каталог, а не версии pytest. Закреплённые версии
  сохранены как воспроизводимый baseline.
- Unit tests выявили циклический импорт через `api/__init__.py`. Импорты routes и
  middleware перенесены внутрь `create_app`, чтобы импорт API schemas не создавал
  приложение целиком.

## Проверки frontend

- Новый TMA: `pnpm check` и production build проходят.
- Legacy TMA: production build проходит.
- `npm ci` legacy TMA сообщил о 12 известных уязвимостях (10 high). Автоматическое
  обновление не выполнялось, поскольку legacy является временным эталоном и
  изменение зависимостей может изменить поведение.

## Итог проверок текущего этапа

- `scripts/check.ps1` проходит полностью: Poetry, Black, isort, flake8, pyright,
  TypeScript check, обе frontend-сборки и четыре Compose-конфигурации.
- 64 backend unit tests, не требующих PostgreSQL, проходят.
- Initial migration успешно компилируется Alembic в PostgreSQL SQL offline.
- Полный `alembic upgrade head`, seed и PostgreSQL integration tests пока не
  выполнены: Docker Desktop на машине не запущен.
