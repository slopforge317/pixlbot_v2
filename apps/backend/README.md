# pixlbot

Backend (FastAPI + Telegram Bot) for Telegram Mini App that provides AI image/video generation via KIE API with credit-based monetization.

## Requirements

- Python 3.12+
- Poetry

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd pixlbot
```

2. Install dependencies:
```bash
poetry install
```

3. Create `.env` file from example:
```bash
cp .env.example .env
```

4. Configure environment variables in `.env`:
```env
# Required
BOT_TOKEN=your_telegram_bot_token
KIE_API_KEY=your_kie_api_key

# Optional (defaults shown)
DATABASE_URL=sqlite+aiosqlite:///./data/pixlbot.db
LOG_LEVEL=INFO
```

## Running

### Development (Polling Mode)

Run bot only (polling mode for development):
```bash
PYTHONPATH=app poetry run python app/main.py
```

Run API server only:
```bash
PYTHONPATH=app poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Production (Webhook Mode)

1. Configure webhook in `.env`:
```env
WEBHOOK_ENABLED=true
WEBHOOK_BASE_URL=https://your-domain.com
WEBHOOK_PATH=/webhook/telegram
WEBHOOK_SECRET=your_random_secret_string
```

2. Run the server:
```bash
PYTHONPATH=app poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

In webhook mode, the bot receives updates through the API server.

### Docker

1. Create `.env` file:
```bash
cp .env.example .env
# Edit .env with your BOT_TOKEN, KIE_API_KEY, etc.
```

2. Build and run:
```bash
docker compose up -d --build
```

3. View logs:
```bash
docker compose logs -f
```

4. Stop:
```bash
docker compose down
```

## Development

### Code Quality

Run in order:
```bash
PYTHONPATH=app poetry run isort .     # Sort imports
PYTHONPATH=app poetry run black .     # Format code
PYTHONPATH=app poetry run flake8 .    # Check style
poetry run pyright                    # Check types
```

### Tests

```bash
PYTHONPATH=app poetry run pytest -q              # All tests
PYTHONPATH=app poetry run pytest tests/test_file.py::test_name -v  # Single test
```

## Project Structure

```
app/
├── api/       # FastAPI endpoints (REST API for TMA)
├── bot/       # aiogram handlers (notifications only)
├── services/  # Business logic, KIE API client
├── db/        # SQLAlchemy models and repositories
├── core/      # Config, logging
└── main.py    # Entry point
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `BOT_TOKEN` | Yes | - | Telegram bot token from @BotFather |
| `KIE_API_KEY` | Yes | - | API key for kie.ai |
| `DATABASE_URL` | No | `sqlite+aiosqlite:///./data/pixlbot.db` | Database connection URL |
| `LOG_LEVEL` | No | `INFO` | Logging level |
| `LOG_DIR` | No | `logs` | Directory for log files |
| `KIE_API_BASE_URL` | No | `https://api.kie.ai` | KIE API base URL |
| `KIE_POLL_INTERVAL` | No | `3.0` | Polling interval in seconds |
| `KIE_POLL_TIMEOUT` | No | `300.0` | Max wait time for generation |
| `INIT_DATA_EXPIRE_SECONDS` | No | `3600` | TMA auth token lifetime |
| `WEBHOOK_ENABLED` | No | `false` | Enable webhook mode |
| `WEBHOOK_BASE_URL` | No | - | Public URL for webhooks |
| `WEBHOOK_PATH` | No | `/webhook/telegram` | Webhook endpoint path |
| `WEBHOOK_SECRET` | No | - | Secret token for webhook verification |

## License

MIT
