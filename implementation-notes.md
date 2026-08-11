# Заметки по реализации

## Решения

- `providers.title` остаётся публичным названием модели без технических суффиксов: например, `Nano Banana 2` и `GPT Image 1.5`.
- `providers.slug` добавляется как обязательный уникальный технический ключ. Он не используется как подпись в интерфейсе.
- Внутренние API-модели получают `input_mode`: `text_only`, `image_required` или `image_optional`.
- Видео-модели не удаляются из БД: seed переводит их providers и модели в `active=false`. Это сохраняет старую историю и внешние ключи.
- Текущий этап меняет каталог, БД и API. Автоматическое переключение реализации и динамическая форма TMA остаются следующим этапом.

## Допущения

- У GPT Image 1.5 параметр `quality` влияет на цену одинаково для Text-to-Image и Image-to-Image, поэтому для обеих реализаций используется `variant: true`.
- Существующие неизвестные providers при migration получают безопасный slug вида `provider-<id>`; известные записи получают человекочитаемые slug.
- ORM создаёт fallback slug из английского `title` только для некаталожных записей и тестов. Seed всегда передаёт явный slug.

## Риски и продолжение

- До следующего этапа TMA продолжит отображать внутренние реализации плоским списком, хотя API уже будет содержать slug и режим ввода.
- Перед production migration нужен backup согласно `docs/database-migration.md`.

## Проверки

- Каталог и защита GPT Image: `3 passed`.
- Полный `scripts/check.ps1`: пройден, включая Black, isort, flake8, pyright, Alembic offline SQL, TMA TypeScript/build и Compose config.
- Полный PostgreSQL test suite не запущен: локальный Docker daemon недоступен (`open //./pipe/docker_engine: The system cannot find the file specified`).
