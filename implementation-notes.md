# Заметки по реализации

## Зафиксированные входные данные

- Test-домен: `tma.pixlbot.ru`.
- GitHub: `https://github.com/slopforge317/pixlbot_v2.git`.
- Порты 80 и 443 на сервере свободны.
- Legacy backup создан, проверен через `pg_restore --list` и скопирован с сервера.
- Контрольная сумма backup:
  `b013c988b027f4d71ac3079f4bdb3bca9b8c3b37290558149d8e65029a02ac5b`.

## Принятые решения

- Первый deployable baseline содержит только `compose.test.yaml`.
- Локальный mock/dev-стенд откладывается; сервер проверяется через реального тестового бота.
- Caddy одновременно служит runtime для TMA, reverse proxy для backend и TLS endpoint.
- Mock Telegram auth удаляется, чтобы server test не содержал bypass production-аутентификации.
- Telegram webhook не используется на первом этапе; bot работает через polling.
- Legacy-БД не подключается физическим volume. Используется только `pg_dump`/`pg_restore`.
- Принятие legacy Alembic history выполняется отдельной явной командой после schema diff.
- Legacy dump содержит три native PostgreSQL enum types, тогда как новая baseline
  использует `VARCHAR`. Добавлен отдельный транзакционный reconciliation шаг.
- Funnel messaging и stale payment cleanup имеют отдельные feature flags и
  отключены на первом test-стенде, чтобы копия legacy-БД не создавала side effects.

## Риски и последующие действия

- Legacy revision несовместима с новой initial migration. Автоматически запускать
  `migrate` сразу после restore нельзя.
- В восстановленной базе могут быть pending funnel messages и другие фоновые записи.
  Их нужно обезвредить до запуска нового бота.
- Seed обновляет модели и цены и деактивирует отсутствующие pricing variants, поэтому
  на восстановленной базе он запускается только после проверки.
- Генерации, KIE callback, S3 uploads, YooKassa и monitoring остаются вне первого этапа.

## Ход реализации

- План сохранён в `plans/001-server-test-deployment.md`.
- Compose сведён к самостоятельному `compose.test.yaml`; dev/prod overlays удалены.
- Monitoring Compose также отложен; конфигурации в `infra/monitoring` сохранены
  для следующего этапа.
- TMA runtime переведён с Nginx на Caddy 2.11.4.
- Добавлен `adopt_legacy_schema.py` с check, enum reconciliation, adoption,
  sanitization и summary.
- Статические проверки backend, auth unit tests, TMA typecheck/build и Compose
  config проходят. Полный Docker test и image/Caddy runtime validation локально
  недоступны, потому что Docker daemon на рабочей машине не запущен.
- Git remote `origin` привязан к `https://github.com/slopforge317/pixlbot_v2.git`;
  удалённый репозиторий не содержит веток и готов к первичной публикации.
- Baseline опубликован в `origin/main`; первичный implementation commit — `56a5125`.
