# Заметки по реализации

## Цель

- Подготовить обычную Alembic-цепочку для развёртывания восстановленного legacy
  dump на test-сервере без ручной подмены revision.

## Зафиксированные решения

- Legacy revision `f7d735a7befd` используется как squashed baseline.
- Пользовательские данные остаются в PostgreSQL dump и не включаются в миграции.
- Все отличия legacy schema от текущей модели оформляются следующей обычной
  Alembic migration.
- Baseline создаёт native enum на чистой БД, а bridge migration переводит их в
  текущие `VARCHAR`; поэтому clean install и restore проходят одну цепочку.
- Постоянные Docker volumes получили явные имена `pixlbot_v2_*`, чтобы данные не
  зависели от будущего переименования Compose project.
- Старый adoption helper удалён. Отдельный `database_tools.py` оставляет только
  test-only sanitization и сводку количества данных.

## Компромиссы и риски

- Dump не включается в репозиторий и не исполняется из Alembic: миграции хранят
  структуру и преобразования, а `pg_restore` переносит реальные данные.
- Полное соответствие dump baseline окончательно подтверждается на сервере через
  `alembic upgrade head` и `alembic check`. При дополнительных отличиях запуск
  backend запрещён до добавления новой migration.
- `sanitize` отменяет pending messages и предназначен только для test-копии; при
  production cutover его нельзя запускать автоматически.

## Ход работы

- Initial migration заменена на squashed legacy baseline `f7d735a7befd`.
- Добавлена обычная migration `20260805_0001` для нормализации трёх enum.
- Compose и deployment docs переведены с adoption workflow на `upgrade head`.
- `scripts/test.ps1` использует отдельный volume
  `pixlbot_pytest_postgres_data` и перед pytest проверяет реальный migration path
  `base → f7d735a7befd → head` на отдельной базе.

## Проверки

- `scripts/check.ps1` проходит: Black, isort, flake8, pyright, Alembic graph и
  offline SQL, TMA typecheck/build, Compose config.
- Offline upgrade и downgrade SQL успешно генерируются для PostgreSQL.
- CLI `database_tools.py` и PowerShell syntax `scripts/test.ps1` проверены.
- Локальный Docker daemon не запущен, поэтому выполнение DDL на живой PostgreSQL
  и полный pytest остаются обязательной первой проверкой на сервере.
