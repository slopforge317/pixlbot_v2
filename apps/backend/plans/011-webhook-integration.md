# План 011: Переход на Webhook для Telegram Bot

**Статус:** DRAFT
**Фаза:** 3.3
**Цель:** Перевести бота с polling на webhook и интегрировать с FastAPI

---

## Текущее состояние

### Архитектура сейчас
```
┌─────────────────┐     ┌─────────────────┐
│  FastAPI API    │     │  Telegram Bot   │
│  (uvicorn)      │     │  (polling)      │
│  :8000          │     │  отдельный      │
│                 │     │  процесс        │
└─────────────────┘     └─────────────────┘
```

**Проблемы polling:**
- Два отдельных процесса (сложнее деплой)
- Постоянные запросы к Telegram API (трафик, задержки)
- Не масштабируется горизонтально

### Архитектура после
```
┌─────────────────────────────────────────┐
│            FastAPI Application          │
│  :8000                                  │
│  ┌─────────────┐  ┌──────────────────┐  │
│  │ /api/*      │  │ /webhook/telegram│  │
│  │ TMA API     │  │ Bot updates      │  │
│  └─────────────┘  └──────────────────┘  │
└─────────────────────────────────────────┘
                    ▲
                    │ POST (updates)
                    │
            ┌───────┴───────┐
            │   Telegram    │
            │   Servers     │
            └───────────────┘
```

**Преимущества webhook:**
- Один процесс (простой деплой)
- Telegram сам отправляет updates (меньше трафика)
- Мгновенная доставка сообщений
- Горизонтальное масштабирование возможно

---

## Ограничения и требования

### Требования Telegram
1. **HTTPS обязателен** — webhook URL должен быть https://
2. **Публичный URL** — Telegram должен достучаться до сервера
3. **Порты:** 443, 80, 88, или 8443
4. **Сертификат:** валидный SSL (Let's Encrypt и др.) или self-signed

### Режимы работы
Нужно поддержать оба режима:
- **Production:** webhook (публичный сервер)
- **Development:** polling (локальная разработка без публичного URL)

---

## Шаги реализации

### Шаг 1: Конфигурация

**Файл:** `app/core/config.py`

Добавить настройки:
```python
# Webhook settings
webhook_enabled: bool = False  # False = polling, True = webhook
webhook_base_url: str = ""     # https://example.com (без trailing slash)
webhook_path: str = "/webhook/telegram"
webhook_secret: str = ""       # Secret token для верификации
```

**Переменные окружения:**
```
WEBHOOK_ENABLED=true
WEBHOOK_BASE_URL=https://pixlbot.example.com
WEBHOOK_PATH=/webhook/telegram
WEBHOOK_SECRET=<random-string-32-chars>
```

### Шаг 2: Webhook endpoint

**Файл:** `app/api/routes/webhook.py` (новый)

```python
from fastapi import APIRouter, Request, HTTPException, Header
from aiogram.types import Update

router = APIRouter()

@router.post("/webhook/telegram")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(None),
) -> dict:
    """Handle incoming Telegram updates via webhook."""
    # 1. Verify secret token
    # 2. Parse update JSON
    # 3. Feed to dispatcher
    # 4. Return OK
```

**Важно:**
- Проверка `X-Telegram-Bot-Api-Secret-Token` header
- Использование `dispatcher.feed_update(bot, update)`
- Быстрый ответ 200 OK (обработка в фоне)

### Шаг 3: Хранение Bot и Dispatcher

**Проблема:** Сейчас bot/dispatcher создаются в `run_bot()` локально.

**Решение:** Использовать FastAPI `app.state` для хранения:

**Файл:** `app/bot/__init__.py` — добавить:
```python
async def setup_bot_webhook(app: FastAPI) -> None:
    """Setup bot and dispatcher for webhook mode."""
    bot = create_bot()
    dp = create_dispatcher()

    # Store in app state
    app.state.bot = bot
    app.state.dispatcher = dp

    # Register webhook
    webhook_url = f"{settings.webhook_base_url}{settings.webhook_path}"
    await bot.set_webhook(
        url=webhook_url,
        secret_token=settings.webhook_secret,
        drop_pending_updates=True,
    )

async def shutdown_bot_webhook(app: FastAPI) -> None:
    """Cleanup bot on shutdown."""
    if hasattr(app.state, "bot"):
        await app.state.bot.delete_webhook()
        await app.state.bot.session.close()
```

### Шаг 4: Интеграция в lifespan

**Файл:** `app/main.py`

```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    setup_logging()
    await create_tables()

    # Setup bot based on mode
    if settings.webhook_enabled:
        await setup_bot_webhook(app)
        logger.info(f"Bot webhook registered: {settings.webhook_base_url}{settings.webhook_path}")

    yield

    # Cleanup
    if settings.webhook_enabled:
        await shutdown_bot_webhook(app)
```

### Шаг 5: Роутер webhook

**Файл:** `app/api/__init__.py`

```python
from api.routes.webhook import router as webhook_router

def create_app() -> FastAPI:
    app = FastAPI(...)

    # ... existing routers ...

    # Webhook router (only if enabled)
    if settings.webhook_enabled:
        app.include_router(webhook_router)

    return app
```

### Шаг 6: Получение bot/dispatcher в endpoint

**Файл:** `app/api/routes/webhook.py`

```python
from fastapi import Request

@router.post("/webhook/telegram")
async def telegram_webhook(request: Request, ...):
    bot = request.app.state.bot
    dispatcher = request.app.state.dispatcher

    data = await request.json()
    update = Update.model_validate(data, context={"bot": bot})
    await dispatcher.feed_update(bot, update)

    return {"ok": True}
```

### Шаг 7: Обновить generation service

**Файл:** `app/services/generation.py`

**Проблема:** Сейчас `process_generation()` создаёт свой bot:
```python
bot = create_bot()  # Создаёт новый instance
```

**Решение:** Передавать bot как параметр или использовать глобальный:

```python
# Вариант 1: Глобальная функция получения bot
def get_bot_instance() -> Bot:
    """Get bot instance (creates new if not in webhook mode)."""
    # В webhook режиме можно кэшировать
    return create_bot()
```

**Примечание:** Для background tasks (BackgroundTasks) создание нового bot instance допустимо, т.к. это просто HTTP клиент.

### Шаг 8: Сохранить polling режим

**Файл:** `app/main.py`

```python
async def run_bot() -> None:
    """Run Telegram bot in polling mode (development)."""
    if settings.webhook_enabled:
        logger.error("Cannot run polling when webhook is enabled")
        return

    # ... existing polling code ...
```

### Шаг 9: Тестирование

**Файл:** `tests/test_api/test_webhook.py` (новый)

Тесты:
1. `test_webhook_valid_update` — корректный update обрабатывается
2. `test_webhook_invalid_secret` — неверный secret → 403
3. `test_webhook_missing_secret` — отсутствует secret → 403
4. `test_webhook_invalid_json` — невалидный JSON → 400
5. `test_webhook_message_update` — message update проходит через dispatcher

**Mock:**
- Мокировать `dispatcher.feed_update`
- Мокировать `bot.set_webhook` / `delete_webhook`

---

## Структура файлов

### Новые файлы
```
app/
├── api/
│   └── routes/
│       └── webhook.py      # NEW: Webhook endpoint
tests/
├── test_api/
│   └── test_webhook.py     # NEW: Webhook tests
```

### Изменяемые файлы
```
app/
├── core/
│   └── config.py           # + webhook settings
├── bot/
│   └── __init__.py         # + setup/shutdown webhook functions
├── api/
│   └── __init__.py         # + webhook router registration
└── main.py                 # + webhook in lifespan
```

---

## Детали реализации

### Формат Telegram Update

```json
{
  "update_id": 123456789,
  "message": {
    "message_id": 1,
    "from": {"id": 123, "first_name": "User"},
    "chat": {"id": 123, "type": "private"},
    "date": 1234567890,
    "text": "/start"
  }
}
```

### Secret Token верификация

Telegram отправляет header:
```
X-Telegram-Bot-Api-Secret-Token: <your-secret>
```

Проверка:
```python
if x_telegram_bot_api_secret_token != settings.webhook_secret:
    raise HTTPException(status_code=403, detail="Invalid secret token")
```

### Генерация secret token

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## Миграция и деплой

### Локальная разработка
```bash
# .env
WEBHOOK_ENABLED=false

# Запуск (два терминала)
uvicorn main:app --reload --port 8000
PYTHONPATH=app poetry run python -m main  # polling
```

### Production
```bash
# .env
WEBHOOK_ENABLED=true
WEBHOOK_BASE_URL=https://pixlbot.example.com
WEBHOOK_SECRET=<generated-secret>

# Запуск (один процесс)
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Nginx конфигурация (пример)
```nginx
server {
    listen 443 ssl;
    server_name pixlbot.example.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## Риски и митигация

| Риск | Вероятность | Влияние | Митигация |
|------|-------------|---------|-----------|
| Webhook не регистрируется | Средняя | Высокое | Логирование ошибок, fallback на polling |
| Telegram не достучаться до сервера | Средняя | Высокое | Проверка firewall, SSL, DNS |
| Потеря updates при перезапуске | Низкая | Среднее | `drop_pending_updates=False` опционально |
| Нагрузка на endpoint | Низкая | Низкое | Быстрая обработка, фоновые задачи |

---

## Rollback план

1. Установить `WEBHOOK_ENABLED=false`
2. Перезапустить приложение
3. Запустить бота в polling режиме отдельно
4. Telegram автоматически переключится обратно на getUpdates

---

## Чеклист готовности

- [ ] Настройки webhook в config.py
- [ ] Endpoint POST /webhook/telegram
- [ ] Secret token верификация
- [ ] Setup webhook в lifespan startup
- [ ] Delete webhook в lifespan shutdown
- [ ] Bot/Dispatcher в app.state
- [ ] Роутер условно подключается
- [ ] Polling режим сохранён
- [ ] Тесты webhook endpoint
- [ ] Документация обновлена

---

## Оценка изменений

| Компонент | Изменения |
|-----------|-----------|
| config.py | +10 строк |
| bot/__init__.py | +30 строк |
| api/__init__.py | +5 строк |
| main.py | +10 строк |
| routes/webhook.py | ~50 строк (новый) |
| test_webhook.py | ~100 строк (новый) |

**Итого:** ~200 строк нового кода
