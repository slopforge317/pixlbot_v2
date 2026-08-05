# План серверного test-стенда

## Цель

Развернуть на сервере единый test-стенд проекта на `tma.pixlbot.ru` с:

- новым Telegram Mini App;
- новым обычным BotFather-ботом в polling mode;
- восстановленной копией legacy PostgreSQL;
- обычной Alembic-цепочкой от legacy baseline;
- автоматическим HTTPS через Caddy;
- публикацией исходников в `slopforge317/pixlbot_v2`.

Генерации, callbacks, S3, платежи и monitoring не входят в первый этап.

## Решения

1. Используется одно самостоятельное окружение `compose.test.yaml`.
2. `compose.dev.yaml` и `compose.prod.yaml` удаляются, пока для них нет отдельного сценария.
3. Caddy обслуживает React SPA, проксирует backend и управляет TLS.
4. На сервере используется реальный Telegram `initData`; mock auth удаляется.
5. Обычный тестовый BotFather-бот использует production Telegram API:
   `TELEGRAM_TEST_MODE=false`.
6. Bot API работает через polling; webhook будет добавлен позже.
7. Legacy volume не подключается. База восстанавливается из проверенного custom dump.
8. Squashed baseline имеет revision `f7d735a7befd` из dump. Следующая обычная
   migration нормализует legacy enum; ручной adoption не используется.
9. Секреты хранятся только в серверном `.env.test` и не коммитятся.

## Этапы

1. Нормализовать Compose, env templates и команды.
2. Перевести TMA runtime с Nginx на Caddy.
3. Добавить legacy baseline, bridge migration и безопасные DB tools.
4. Обновить deployment/database документацию.
5. Проверить `.gitignore` и выполнить secret scan.
6. Запустить статические проверки, тесты, frontend build и Compose validation.
7. Настроить Git remote на `https://github.com/slopforge317/pixlbot_v2.git`.
8. После успешной проверки создать commit и отправить `main`.

## Серверный порядок запуска

1. Настроить DNS `tma.pixlbot.ru` на сервер и открыть 80/443.
2. Клонировать репозиторий в отдельный каталог.
3. Создать `.env.test` из `.env.test.example` и заполнить секреты.
4. Запустить только PostgreSQL.
5. Восстановить legacy dump в новый volume.
6. Проверить legacy revision `f7d735a7befd`.
7. Выполнить обычный `alembic upgrade head`, затем `alembic check`.
8. Обезвредить pending фоновые сообщения в копии БД.
9. Запустить seed вручную и проверить данные.
10. Запустить весь Compose и проверить Caddy certificate, health, bot и TMA.

## Критерии готовности

- `https://tma.pixlbot.ru/health` возвращает HTTP 200;
- сертификат публично доверенный;
- новый бот отвечает на `/start`;
- TMA открывается из Telegram и принимает реальный `initData`;
- пользователь, баланс и модели читаются из восстановленной БД;
- `alembic current` показывает новую baseline/head;
- `alembic check` не находит schema diff;
- restart Compose сохраняет PostgreSQL и Caddy certificates;
- старые пользователи не получают сообщения от тестового бота.
