# Technology Stack

## Runtime

- **Language:** Python 3.12+
- **OS:** Linux Ubuntu
- **Shell:** bash

## Dependencies (Production)

| Package | Version | Purpose |
|---------|---------|---------|
| aiogram | 3.24.x | Telegram Bot API framework |
| fastapi | 0.128.x | REST API framework |
| uvicorn | 0.40.x | ASGI server |
| httpx | 0.28.x | Async HTTP client |
| sqlalchemy | 2.0.x | ORM and database toolkit |
| asyncpg | — | Async PostgreSQL driver |
| pydantic-settings | 2.12.x | Configuration management |
| aiofiles | 25.1.x | Async file operations |
| loguru | 0.7.x | Logging library |

## Dependencies (Development)

| Package | Version | Purpose |
|---------|---------|---------|
| pytest | 9.0.x | Testing framework |
| pytest-asyncio | 1.3.x | Async test support |
| isort | 7.0.x | Import sorting |
| black | 25.12.x | Code formatting |
| flake8 | 7.3.x | Linting |
| pyright | 1.1.x | Type checking |

## Configuration

Environment variables loaded via `pydantic-settings` from `.env` file:

| Variable | Default | Description |
|----------|---------|-------------|
| `BOT_TOKEN` | — | Telegram bot token (required) |
| `DATABASE_URL` | `postgresql+asyncpg://...` | PostgreSQL connection string |
| `LOG_LEVEL` | `INFO` | Logging level |
| `LOG_DIR` | `logs` | Log files directory |
| `LOG_ROTATION` | `10 MB` | Log file rotation size |
| `LOG_RETENTION` | `14 days` | Log retention period |
| `KIE_API_KEY` | — | KIE.ai API key (required for generation) |
| `KIE_API_BASE_URL` | `https://api.kie.ai` | KIE API base URL |
| `KIE_POLL_INTERVAL` | `3.0` | Seconds between status polls |
| `KIE_POLL_TIMEOUT` | `300.0` | Max wait time for generation |
| `KIE_CALLBACK_ENABLED` | `false` | Use per-task KIE callback instead of foreground polling |
| `KIE_CALLBACK_SECRET` | — | URL-safe secret in callback path |
| `KIE_WEBHOOK_HMAC_KEY` | — | KIE `webhookHmacKey` used for HMAC-SHA256 verification |
| `KIE_WEBHOOK_MAX_AGE_SECONDS` | `300` | Maximum accepted callback timestamp age |
| `KIE_RECONCILIATION_INTERVAL_SECONDS` | `60` | Missed-callback reconciliation interval |
| `KIE_RECONCILIATION_STALE_SECONDS` | `60` | Minimum job age before reconciliation |
| `KIE_RECONCILIATION_BATCH_SIZE` | `100` | Maximum jobs checked per reconciliation pass |
| `YOOKASSA_PROVIDER_TOKEN` | — | Telegram Payments provider token issued by BotFather |
| `YOOKASSA_TAX_SYSTEM_CODE` | `2` | Tax system code for YooKassa receipt data |
| `YOOKASSA_VAT_CODE` | `1` | VAT code for YooKassa receipt items |
| `YOOKASSA_PAYMENT_SUBJECT` | `service` | Receipt payment subject |
| `YOOKASSA_PAYMENT_MODE` | `full_payment` | Receipt payment mode |

## Logging

- **Library:** loguru
- **Output:** stdout + file `logs/app.log`
- **Rotation:** by size (default 10 MB)
- **Retention:** configurable (default 14 days)
- **Format:** `{time} | {level} | {name}:{function}:{line} - {message}`

## Database

- **Development & Production:** PostgreSQL (async via asyncpg)
- **Migrations:** Alembic (deferred, using `create_tables()` for now)
- **Seeding:** `scripts/seed_db.py` loads typed YAML files from `catalog/models`

## External APIs

### KIE.ai API
- **Base URL:** `https://api.kie.ai`
- **Auth:** Bearer token
- **Endpoints:**
  - `POST /api/v1/jobs/createTask` — create generation task
  - `GET /api/v1/jobs/recordInfo?taskId=xxx` — get task status
- **Rate limits:**
  - 20 requests / 10 seconds (task creation)
  - 10 requests / second (status polling)
- **Result storage:** URLs valid for ~24 hours

### Telegram Payments / YooKassa
- BotFather connects the bot to the YooKassa test or live provider and issues
  `YOOKASSA_PROVIDER_TOKEN`.
- Backend sends `sendInvoice` with prices in kopecks, mandatory email collection,
  and YooKassa `provider_data.receipt` fiscal attributes.
- `PreCheckoutQuery` is answered within the Telegram Update flow; a
  `SuccessfulPayment` stores both Telegram and YooKassa charge IDs and creates
  one immutable deposit transaction.
- Direct YooKassa REST API credentials and a separate YooKassa webhook are not
  used for new payments.

## Tool Configuration

### pytest
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

### black
```toml
[tool.black]
line-length = 88
target-version = ["py312"]
```

### isort
```toml
[tool.isort]
profile = "black"
line_length = 88
```

### pyright
```toml
[tool.pyright]
pythonVersion = "3.12"
typeCheckingMode = "basic"
```
