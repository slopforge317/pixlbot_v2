# Развёртывание test-стенда

Test-домен: `tma.pixlbot.ru`.

Эта инструкция предполагает, что DNS указывает на сервер, порты 80/443 свободны,
а проверенный legacy dump уже скопирован в безопасное место.

## 1. Получить проект

```bash
cd /home/bot
git clone https://github.com/slopforge317/pixlbot_v2.git pixlbot-next
cd pixlbot-next
```

## 2. Настроить окружение

```bash
cp .env.test.example .env.test
chmod 600 .env.test
nano .env.test
```

Обязательно замените `BOT_TOKEN`, `POSTGRES_PASSWORD`, `WEBHOOK_SECRET` и
`KIE_CALLBACK_SECRET`. Для обычного тестового BotFather-бота оставьте:

```dotenv
APP_DOMAIN=tma.pixlbot.ru
TMA_URL=https://tma.pixlbot.ru
TELEGRAM_BOT_ENABLED=true
TELEGRAM_TEST_MODE=false
WEBHOOK_ENABLED=false
FUNNEL_ENABLED=false
PAYMENT_CLEANUP_ENABLED=false
```

Для `POSTGRES_PASSWORD` используйте длинное значение только из латинских букв и
цифр: Compose подставляет его и в PostgreSQL, и в URL подключения backend.

Не публикуйте `.env.test` и не присылайте его содержимое в чат.

## 3. Проверить Compose

```bash
docker compose \
  --env-file .env.test \
  -f compose.test.yaml \
  config --quiet
```

## 4. Запустить только новый PostgreSQL

```bash
docker compose \
  --env-file .env.test \
  -f compose.test.yaml \
  up -d postgres
```

Проверьте, что используется новый project `pixlbot-next-test`, а не legacy
containers или volumes.

## 5. Восстановить legacy dump

Команда ниже изменяет только новую test-БД. Перед выполнением проверьте путь к
backup и имя Compose project.

```bash
docker compose \
  --env-file .env.test \
  -f compose.test.yaml \
  exec -T postgres \
  pg_restore \
    --username=pixlbot \
    --dbname=pixlbot \
    --clean \
    --if-exists \
    --no-owner \
    --no-privileges \
  < /home/bot/pixlbot-backups/pixlbot_20260731_080053.dump
```

После restore не запускайте весь Compose: сначала нужно принять legacy schema.

## 6. Проверить и согласовать legacy schema

```bash
docker compose \
  --env-file .env.test \
  -f compose.test.yaml \
  --profile tools \
  run --rm db-legacy check
```

Первый check должен показать различия трёх native PostgreSQL enums. Legacy schema
использует native enum types, а новая baseline — `VARCHAR`. Согласуйте их явной
транзакционной командой:

```bash
docker compose \
  --env-file .env.test \
  -f compose.test.yaml \
  --profile tools \
  run --rm db-legacy reconcile-enums --confirm RECONCILE_LEGACY_ENUMS
```

Повторите `db-legacy check`. Adoption разрешён только если revision равна
`f7d735a7befd`, а schema diff теперь пуст:

```bash
docker compose \
  --env-file .env.test \
  -f compose.test.yaml \
  --profile tools \
  run --rm db-legacy adopt --confirm ADOPT_LEGACY_SCHEMA
```

Затем проверьте Alembic:

```bash
docker compose \
  --env-file .env.test \
  -f compose.test.yaml \
  run --rm migrate python -m alembic current

docker compose \
  --env-file .env.test \
  -f compose.test.yaml \
  run --rm migrate python -m alembic check
```

Если после reconciliation schema diff не пуст, операция откатится. Сохраните
вывод и не изменяйте revision вручную.

## 7. Обезвредить фоновые сообщения

```bash
docker compose \
  --env-file .env.test \
  -f compose.test.yaml \
  --profile tools \
  run --rm db-legacy sanitize --confirm SANITIZE_LEGACY_TEST_DATA
```

Команда отменяет pending scheduled messages и выключает funnel steps в копии БД.
Кроме того, `FUNNEL_ENABLED=false` и `PAYMENT_CLEANUP_ENABLED=false` не дают
backend снова запустить эти фоновые обработчики на первом стенде.

Проверьте количество данных:

```bash
docker compose \
  --env-file .env.test \
  -f compose.test.yaml \
  --profile tools \
  run --rm db-legacy summary
```

## 8. Выполнить seed

Seed обновляет каталог моделей и цены. Запускайте его только после проверки
restore и summary:

```bash
docker compose \
  --env-file .env.test \
  -f compose.test.yaml \
  --profile tools \
  run --rm seed
```

## 9. Запустить приложение

```bash
docker compose \
  --env-file .env.test \
  -f compose.test.yaml \
  up -d --build
```

Caddy автоматически запросит сертификат для `tma.pixlbot.ru`. DNS должен уже
указывать на сервер, а TCP 80/443 должны быть доступны извне.

## 10. Проверка

```bash
docker compose --env-file .env.test -f compose.test.yaml ps
docker compose --env-file .env.test -f compose.test.yaml logs --tail=100 tma backend
curl --fail https://tma.pixlbot.ru/health
```

После этого настройте Menu Button/Mini App URL нового бота на
`https://tma.pixlbot.ru` и проверьте `/start`, открытие TMA, пользователя, баланс
и список моделей.

## Откат

```bash
docker compose --env-file .env.test -f compose.test.yaml stop
```

Не используйте `down -v`: PostgreSQL и Caddy certificates находятся в named
volumes. Legacy project остаётся отдельным и может быть запущен независимо.
