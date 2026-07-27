# Phase 2.1: Telegram Bot Basic Commands

**Status:** COMPLETED
**Dependencies:** Phase 1.1 (DB models, repositories)
**Result:** Working Telegram bot with /start, /help, /balance commands

---

## Objective

Implement basic Telegram bot commands using aiogram 3.x:
- `/start` — user registration, welcome message
- `/help` — help/usage info
- `/balance` — show user's credit balance

---

## Current State Analysis

### Already Implemented
- **DB Models:** User, Transaction (with all fields from schema)
- **Repositories:**
  - `UserRepository.get_or_create()` — register or get user
  - `UserRepository.get_balance()` — calculate balance from transactions
- **Config:** `bot_token` in Settings
- **Dependencies:** aiogram 3.x in pyproject.toml

### Not Implemented
- Bot initialization and dispatcher setup
- Command handlers
- Message texts (i18n-ready structure)
- Bot entry point

---

## File Structure

```
app/bot/
├── __init__.py          # Bot instance, dispatcher
├── handlers/
│   ├── __init__.py      # Router registration
│   └── commands.py      # /start, /help, /balance handlers
├── middlewares/
│   ├── __init__.py
│   └── db.py            # DB session middleware
├── keyboards/
│   └── __init__.py      # (empty for now, future keyboards)
└── texts.py             # Message texts (for future i18n)
```

---

## Implementation Steps

### Step 1: Message Texts
**File:** `app/bot/texts.py`

```python
# Centralized message texts for easy editing/i18n
WELCOME_NEW = "..."
WELCOME_BACK = "..."
HELP_TEXT = "..."
BALANCE_TEXT = "..."
```

**Acceptance:** File created with all message templates.

---

### Step 2: DB Session Middleware
**File:** `app/bot/middlewares/db.py`

Middleware that provides DB session to handlers via `data["session"]`.

```python
class DbSessionMiddleware(BaseMiddleware):
    def __init__(self, session_maker: async_sessionmaker):
        self.session_maker = session_maker

    async def __call__(self, handler, event, data):
        async with self.session_maker() as session:
            data["session"] = session
            return await handler(event, data)
```

**Acceptance:** Middleware injects session into handler data.

---

### Step 3: Command Handlers
**File:** `app/bot/handlers/commands.py`

```python
router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession):
    # 1. Extract UTM from deep link (if any)
    # 2. get_or_create user via UserRepository
    # 3. Send welcome message (different for new/existing)

@router.message(Command("help"))
async def cmd_help(message: Message):
    # Send help text

@router.message(Command("balance"))
async def cmd_balance(message: Message, session: AsyncSession):
    # 1. Get user by telegram_id
    # 2. Get balance via UserRepository.get_balance()
    # 3. Send formatted balance
```

**Acceptance:** All three commands respond correctly.

---

### Step 4: Bot Initialization
**File:** `app/bot/__init__.py`

```python
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.core.config import settings
from app.db.session import async_session_maker
from app.bot.middlewares.db import DbSessionMiddleware
from app.bot.handlers import commands

def create_bot() -> Bot:
    return Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

def create_dispatcher() -> Dispatcher:
    dp = Dispatcher()

    # Register middlewares
    dp.message.middleware(DbSessionMiddleware(async_session_maker))

    # Register routers
    dp.include_router(commands.router)

    return dp
```

**Acceptance:** `create_bot()` and `create_dispatcher()` functions work.

---

### Step 5: Entry Point
**File:** `app/main.py` (update)

```python
import asyncio
from app.bot import create_bot, create_dispatcher
from app.db.session import init_db

async def main():
    await init_db()  # Create tables if not exist

    bot = create_bot()
    dp = create_dispatcher()

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
```

**Acceptance:** `PYTHONPATH=app poetry run python app/main.py` starts the bot.

---

### Step 6: Tests
**Files:** `tests/test_bot/`

- `test_handlers.py` — unit tests for handlers with mocked session
- Test scenarios:
  - /start creates new user
  - /start returns existing user
  - /start with UTM parameter
  - /help returns help text
  - /balance returns correct balance

**Acceptance:** `PYTHONPATH=app poetry run pytest tests/test_bot/ -v` passes.

---

## Message Texts (Draft)

### /start (new user)
```
Welcome to PixlBot!

Generate stunning images and videos with AI:
- Seedream, Nano Banana Pro (images)
- Kling, Veo, Sora (videos)

Your starting balance: 0 credits
Use /help to see available commands.
```

### /start (existing user)
```
Welcome back, {first_name}!

Your balance: {balance} credits
Use /help to see available commands.
```

### /help
```
Available commands:

/start — Start the bot
/help — Show this message
/balance — Check your credit balance

Coming soon:
/generate — Generate images/videos
/history — View generation history
/buy — Purchase credits
```

### /balance
```
Your balance: {balance} credits
```

---

## Risks

1. **Bot token not set** — app will crash on start → add validation in config
2. **DB not initialized** — handlers will fail → ensure init_db() runs first
3. **aiogram 3.x breaking changes** — use context7 MCP to check current docs

---

## Rollback Strategy

All changes are in new files under `app/bot/`. To rollback:
1. Delete `app/bot/handlers/`, `app/bot/middlewares/`
2. Restore empty `app/bot/__init__.py`
3. Restore original `app/main.py`

---

## Checklist

- [x] `app/bot/texts.py` created
- [x] `app/bot/middlewares/db.py` created
- [x] `app/bot/handlers/commands.py` created
- [x] `app/bot/__init__.py` updated with bot factory
- [x] `app/main.py` updated with entry point
- [x] Tests written and passing
- [ ] Manual test: bot responds to /start, /help, /balance
- [x] Code quality checks pass (isort, black, flake8, pyright)
