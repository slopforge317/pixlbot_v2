# Развёртывание test-стенда

Test-домен: `tma.pixlbot.ru`.

Инструкция предполагает, что DNS уже указывает на сервер, TCP 80/443 свободны,
а проверенный legacy dump находится вне каталога репозитория.

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

Замените `BOT_TOKEN`, `POSTGRES_PASSWORD`, `WEBHOOK_SECRET` и
`KIE_CALLBACK_SECRET`. Для первого запуска оставьте:

```dotenv
APP_DOMAIN=tma.pixlbot.ru
TMA_URL=https://tma.pixlbot.ru
POSTGRES_VOLUME_NAME=pixlbot_v2_postgres_data
TELEGRAM_BOT_ENABLED=true
TELEGRAM_TEST_MODE=false
WEBHOOK_ENABLED=false
FUNNEL_ENABLED=false
PAYMENT_CLEANUP_ENABLED=false
S3_UPLOAD_MAX_SIZE_BYTES=31457280
```

Для `POSTGRES_PASSWORD` используйте длинное значение только из латинских букв и
цифр: Compose подставляет его также в URL подключения backend.

## 3. Проверить конфигурацию и backup

```bash
docker compose --env-file .env.test -f compose.test.yaml config --quiet

echo \
  "b013c988b027f4d71ac3079f4bdb3bca9b8c3b37290558149d8e65029a02ac5b  /home/bot/pixlbot-backups/pixlbot_20260731_080053.dump" \
  | sha256sum --check
```

Если dump был перемещён, замените только путь, не checksum.

## 4. Запустить постоянный PostgreSQL

```bash
docker compose --env-file .env.test -f compose.test.yaml up -d postgres
docker volume inspect pixlbot_v2_postgres_data
```

Явное имя volume не зависит от имени Compose project. Будущая смена имени
окружения не создаст незаметно другую пустую БД.

## 5. Восстановить legacy dump

Следующая команда перезаписывает целевую БД `pixlbot` внутри нового volume.
Backend на этом этапе ещё не запущен.

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

Проверьте, что dump содержит ожидаемую legacy revision:

```bash
docker compose \
  --env-file .env.test \
  -f compose.test.yaml \
  run --rm migrate python -m alembic current
```

Ожидаемый результат: `f7d735a7befd`.

## 6. Применить обычные миграции

```bash
docker compose \
  --env-file .env.test \
  -f compose.test.yaml \
  run --rm migrate

docker compose \
  --env-file .env.test \
  -f compose.test.yaml \
  run --rm migrate python -m alembic current

docker compose \
  --env-file .env.test \
  -f compose.test.yaml \
  run --rm migrate python -m alembic check
```

Ожидаемый head: `20260811_0001`. `alembic check` должен сообщить, что новых
операций не обнаружено. При другом результате остановитесь и сохраните вывод.

## 7. Проверить и обезвредить test-данные

Сначала сравните количество строк с ожидаемым:

```bash
docker compose \
  --env-file .env.test \
  -f compose.test.yaml \
  --profile tools \
  run --rm db-tools summary
```

Для test-бота отмените старые pending messages и отключите funnel steps:

```bash
docker compose \
  --env-file .env.test \
  -f compose.test.yaml \
  --profile tools \
  run --rm db-tools sanitize --confirm SANITIZE_LEGACY_TEST_DATA
```

Это test-only операция. При будущем production cutover решение о сохранении
pending messages принимается отдельно. Дополнительно фоновые workers выключены
через `.env.test`.

## 8. Обновить каталог моделей

Seed изменяет providers, models, pricing variants и packages. Выполните его после
проверки summary:

```bash
docker compose \
  --env-file .env.test \
  -f compose.test.yaml \
  --profile tools \
  run --rm seed
```

## 9. Запустить приложение

```bash
docker compose --env-file .env.test -f compose.test.yaml up -d --build
```

Повторный запуск migration будет no-op. Caddy запросит сертификат для
`tma.pixlbot.ru` и сохранит ACME state в постоянном volume.

## 10. Smoke-проверка

```bash
docker compose --env-file .env.test -f compose.test.yaml ps
docker compose --env-file .env.test -f compose.test.yaml logs --tail=100 migrate backend tma
curl --fail https://tma.pixlbot.ru/health
```

Настройте Menu Button нового бота на `https://tma.pixlbot.ru` и проверьте
`/start`, открытие TMA, пользователя, баланс и список моделей.

## Последующие deploy

До каждой новой migration создайте backup текущего volume:

```bash
mkdir -p /home/bot/pixlbot-backups
BACKUP_FILE="/home/bot/pixlbot-backups/predeploy_$(date +%Y%m%d_%H%M%S).dump"

docker compose \
  --env-file .env.test \
  -f compose.test.yaml \
  exec -T postgres \
  pg_dump --username=pixlbot --dbname=pixlbot --format=custom \
  > "$BACKUP_FILE"

sha256sum "$BACKUP_FILE" > "$BACKUP_FILE.sha256"

git pull --ff-only
docker compose --env-file .env.test -f compose.test.yaml build
docker compose --env-file .env.test -f compose.test.yaml run --rm migrate
docker compose --env-file .env.test -f compose.test.yaml run --rm migrate python -m alembic current
docker compose --env-file .env.test -f compose.test.yaml run --rm migrate python -m alembic check
docker compose --env-file .env.test -f compose.test.yaml --profile tools run --rm seed
docker compose --env-file .env.test -f compose.test.yaml up -d
curl --fail https://tma.pixlbot.ru/health
```

После обновления каталога проверьте активные публичные модели:

```bash
docker compose \
  --env-file .env.test \
  -f compose.test.yaml \
  exec -T postgres \
  psql --username=pixlbot --dbname=pixlbot \
  --command="SELECT slug, title, sort_order FROM providers WHERE active ORDER BY sort_order, id;"
```

Ожидаются только image-модели: Nano Banana 2, Nano Banana Pro, Seedream 5 Lite,
Seedream 4.5 и GPT Image 1.5. Sora/Kling должны отсутствовать.

## Остановка и восстановление

```bash
docker compose --env-file .env.test -f compose.test.yaml stop
```

Не используйте `down -v`. Если migration повредила данные, не выполняйте
непроверенный downgrade на рабочей БД: остановите приложение и восстановите
последний predeploy dump в проверенный volume.
