# План 002: Реализация аутентификации TMA (Шаг 2.1)

**Статус:** DONE
**Зависимости:** Фаза 1 (завершена) — User модель, UserRepository, базовая инфраструктура
**Цель:** Валидация Telegram InitData + Middleware авторизации + Получение/создание пользователя

---

## Обзор

Telegram Mini App (TMA) передаёт `initData` — подписанную строку с данными пользователя. Backend должен:
1. Валидировать подпись HMAC-SHA256
2. Проверять свежесть данных (auth_date)
3. Извлекать данные пользователя
4. Создавать/получать пользователя в БД
5. Предоставлять доступ к защищённым эндпоинтам

---

## Архитектура решения

```
TMA Frontend
    │
    │ Authorization: tma <initData>
    ▼
┌─────────────────────────────────────────────────────────┐
│                    FastAPI Endpoint                      │
│                                                          │
│  @router.get("/api/me")                                 │
│  async def get_me(user: User = Depends(get_current_user)):│
│      return user                                         │
└─────────────────────────────────────────────────────────┘
    │
    │ Depends(get_current_user)
    ▼
┌─────────────────────────────────────────────────────────┐
│              get_current_user() dependency               │
│                                                          │
│  1. Извлечь initData из заголовка Authorization         │
│  2. Вызвать validate_init_data()                        │
│  3. Вызвать get_or_create_user()                        │
│  4. Вернуть объект User                                 │
└─────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│           validate_init_data() — core logic             │
│                                                          │
│  1. Парсинг query string                                │
│  2. Извлечение и проверка hash                          │
│  3. Формирование data-check-string                      │
│  4. Вычисление HMAC-SHA256                              │
│  5. Сравнение хешей                                     │
│  6. Проверка auth_date (свежесть)                       │
│  7. Парсинг user JSON                                   │
└─────────────────────────────────────────────────────────┘
```

---

## Алгоритм валидации Telegram InitData

### Источник
[Telegram Core Documentation](https://core.telegram.org/bots/webapps#validating-data-received-via-the-web-app)

### Шаги валидации

1. **Парсинг initData** (URL-encoded query string):
   ```
   query_id=AAHdF6IQ...&user=%7B%22id%22...&auth_date=1234567890&hash=abc123...
   ```

2. **Извлечение hash** — сохранить отдельно, убрать из данных

3. **Формирование data-check-string**:
   - Отсортировать пары key=value по ключу (алфавитно)
   - Соединить через `\n` (0x0A)
   ```
   auth_date=1234567890
   query_id=AAHdF6IQAAAAAAN0XohGezM
   user={"id":123456789,"first_name":"John",...}
   ```

4. **Вычисление secret_key**:
   ```python
   secret_key = HMAC_SHA256(key="WebAppData", data=BOT_TOKEN)
   ```

5. **Вычисление hash**:
   ```python
   calculated_hash = HMAC_SHA256(key=secret_key, data=data_check_string).hexdigest()
   ```

6. **Сравнение** `calculated_hash == received_hash`

7. **Проверка auth_date** — не старше N секунд (защита от replay attacks)

---

## Структура файлов

```
app/
├── api/
│   ├── __init__.py           # FastAPI app factory
│   ├── deps.py               # Dependencies (auth, db session)
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── auth.py           # TelegramInitData, TelegramUser schemas
│   │   └── user.py           # UserResponse, UserBalance schemas
│   └── routes/
│       ├── __init__.py       # API router aggregator
│       └── users.py          # GET /api/me, etc.
├── core/
│   └── config.py             # + INIT_DATA_EXPIRE_SECONDS
└── services/
    └── auth/
        ├── __init__.py
        ├── init_data.py      # validate_init_data(), parse_init_data()
        └── exceptions.py     # AuthError, InvalidInitData, ExpiredInitData
```

---

## Детальный план реализации

### Шаг 1: Конфигурация

**Файл:** `app/core/config.py`

**Добавить:**
```python
class Settings(BaseSettings):
    # ... existing ...

    # Auth settings
    init_data_expire_seconds: int = 3600  # 1 hour default
```

**Обоснование:**
- `init_data_expire_seconds` — время жизни initData (защита от replay attacks)
- Bot token уже есть в конфиге (`bot_token`)

---

### Шаг 2: Исключения аутентификации

**Файл:** `app/services/auth/exceptions.py`

```python
class AuthError(Exception):
    """Base authentication error."""
    pass

class InvalidInitDataError(AuthError):
    """InitData signature validation failed."""
    pass

class ExpiredInitDataError(AuthError):
    """InitData auth_date is too old."""
    pass

class MissingInitDataError(AuthError):
    """Authorization header missing or malformed."""
    pass
```

---

### Шаг 3: Pydantic схемы для InitData

**Файл:** `app/api/schemas/auth.py`

```python
from pydantic import BaseModel, Field
from typing import Optional

class TelegramUser(BaseModel):
    """User data from Telegram InitData."""
    id: int
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    language_code: Optional[str] = None
    is_premium: Optional[bool] = None
    photo_url: Optional[str] = None

class TelegramInitData(BaseModel):
    """Parsed and validated Telegram InitData."""
    query_id: Optional[str] = None
    user: TelegramUser
    auth_date: int
    hash: str
    chat_type: Optional[str] = None
    chat_instance: Optional[str] = None
    start_param: Optional[str] = None
```

---

### Шаг 4: Сервис валидации InitData

**Файл:** `app/services/auth/init_data.py`

```python
import hmac
import hashlib
import json
import time
from urllib.parse import parse_qs, unquote

from core.config import settings
from .exceptions import InvalidInitDataError, ExpiredInitDataError, MissingInitDataError
from api.schemas.auth import TelegramInitData, TelegramUser


def validate_init_data(init_data_raw: str) -> TelegramInitData:
    """
    Validate Telegram Mini App InitData.

    Algorithm:
    1. Parse URL-encoded query string
    2. Extract and remove 'hash' parameter
    3. Build data-check-string (sorted key=value pairs joined by \\n)
    4. Calculate HMAC-SHA256 with secret derived from bot token
    5. Compare hashes
    6. Check auth_date freshness
    7. Parse and return structured data

    Raises:
        MissingInitDataError: If initData is empty or missing required fields
        InvalidInitDataError: If hash validation fails
        ExpiredInitDataError: If auth_date is too old

    Returns:
        TelegramInitData with parsed user data
    """
    ...


def _calculate_hash(data_check_string: str, bot_token: str) -> str:
    """Calculate HMAC-SHA256 hash for InitData validation."""
    secret_key = hmac.new(
        key=b"WebAppData",
        msg=bot_token.encode(),
        digestmod=hashlib.sha256
    ).digest()

    return hmac.new(
        key=secret_key,
        msg=data_check_string.encode(),
        digestmod=hashlib.sha256
    ).hexdigest()


def _build_data_check_string(params: dict[str, str]) -> str:
    """Build sorted data-check-string from params (excluding hash)."""
    sorted_params = sorted(params.items(), key=lambda x: x[0])
    return "\n".join(f"{k}={v}" for k, v in sorted_params)
```

---

### Шаг 5: API Schemas для User

**Файл:** `app/api/schemas/user.py`

```python
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class UserResponse(BaseModel):
    """User profile response for TMA."""
    user_id: int
    telegram_user_id: int
    first_name: str
    last_name: Optional[str]
    username: Optional[str]
    balance: int
    created_at: datetime

    model_config = {"from_attributes": True}

class UserBalanceResponse(BaseModel):
    """Quick balance check response."""
    balance: int
```

---

### Шаг 6: FastAPI Dependencies

**Файл:** `app/api/deps.py`

```python
from typing import Annotated
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import async_session_maker
from db.models import User
from db.repositories.user import UserRepository
from services.auth.init_data import validate_init_data
from services.auth.exceptions import AuthError, InvalidInitDataError, ExpiredInitDataError


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for database session."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


DBSession = Annotated[AsyncSession, Depends(get_db_session)]


async def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
    session: DBSession = None,
) -> User:
    """
    Authenticate user via Telegram InitData.

    Expected header format: Authorization: tma <initData>

    1. Extract initData from Authorization header
    2. Validate initData signature and freshness
    3. Get or create user in database
    4. Return User object

    Raises:
        HTTPException 401: Missing or invalid Authorization header
        HTTPException 401: Invalid initData signature
        HTTPException 401: Expired initData
    """
    if not authorization or not authorization.startswith("tma "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
            headers={"WWW-Authenticate": "tma"},
        )

    init_data_raw = authorization[4:]  # Remove "tma " prefix

    try:
        init_data = validate_init_data(init_data_raw)
    except InvalidInitDataError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid initData signature",
        )
    except ExpiredInitDataError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="InitData expired",
        )
    except AuthError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )

    # Get or create user
    user_repo = UserRepository(session)
    user, created = await user_repo.get_or_create(
        telegram_user_id=init_data.user.id,
        chat_id=init_data.user.id,  # In TMA context, chat_id = user_id
        first_name=init_data.user.first_name,
        last_name=init_data.user.last_name,
        username=init_data.user.username,
    )

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
```

---

### Шаг 7: API Router — Users

**Файл:** `app/api/routes/users.py`

```python
from fastapi import APIRouter

from api.deps import CurrentUser, DBSession
from api.schemas.user import UserResponse
from db.repositories.user import UserRepository

router = APIRouter(prefix="/api", tags=["users"])


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    user: CurrentUser,
    session: DBSession,
) -> UserResponse:
    """
    Get current user profile with balance.

    Requires: Authorization: tma <initData>
    """
    user_repo = UserRepository(session)
    balance = await user_repo.get_balance(user.user_id)

    return UserResponse(
        user_id=user.user_id,
        telegram_user_id=user.telegram_user_id,
        first_name=user.first_name,
        last_name=user.last_name,
        username=user.username,
        balance=balance,
        created_at=user.created_at,
    )
```

---

### Шаг 8: FastAPI Application Factory

**Файл:** `app/api/__init__.py`

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import users


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title="pixlbot API",
        description="Backend API for pixlbot TMA",
        version="0.1.0",
    )

    # CORS middleware for TMA
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # TMA runs in iframe, origin varies
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(users.router)

    return app
```

---

### Шаг 9: Интеграция в main.py

**Файл:** `app/main.py`

Обновить для запуска FastAPI + Bot:

```python
import asyncio
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from api import create_app
from bot import create_bot, create_dispatcher
from db.session import create_tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    await create_tables()
    yield


def create_application() -> FastAPI:
    """Create main FastAPI application with lifespan."""
    app = create_app()
    app.router.lifespan_context = lifespan
    return app


app = create_application()


async def run_bot():
    """Run Telegram bot polling."""
    bot = create_bot()
    dp = create_dispatcher()
    await dp.start_polling(bot)


if __name__ == "__main__":
    # For development: run bot only
    # Production: uvicorn app.main:app + separate bot process
    asyncio.run(run_bot())
```

---

### Шаг 10: Тесты

**Файл:** `tests/test_api/conftest.py`

```python
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from api import create_app
from db.base import Base


@pytest.fixture
async def test_app():
    """Create test FastAPI app with in-memory database."""
    ...


@pytest.fixture
async def client(test_app):
    """Async HTTP client for testing."""
    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://test"
    ) as ac:
        yield ac
```

**Файл:** `tests/test_api/test_auth.py`

```python
import hmac
import hashlib
import time
import json
import pytest
from urllib.parse import urlencode


def generate_valid_init_data(bot_token: str, user_data: dict, auth_date: int = None) -> str:
    """Generate valid initData for testing."""
    ...


class TestInitDataValidation:
    """Tests for Telegram InitData validation."""

    async def test_valid_init_data_returns_user(self, client):
        """Valid initData should return user profile."""
        ...

    async def test_invalid_hash_returns_401(self, client):
        """Invalid hash should return 401."""
        ...

    async def test_expired_init_data_returns_401(self, client):
        """Expired initData should return 401."""
        ...

    async def test_missing_auth_header_returns_401(self, client):
        """Missing Authorization header should return 401."""
        ...

    async def test_malformed_init_data_returns_401(self, client):
        """Malformed initData should return 401."""
        ...

    async def test_new_user_is_created(self, client, db_session):
        """New user should be created on first auth."""
        ...

    async def test_existing_user_is_returned(self, client, db_session):
        """Existing user should be returned on subsequent auth."""
        ...
```

**Файл:** `tests/test_services/test_auth/test_init_data.py`

```python
"""Unit tests for init_data validation service."""

class TestCalculateHash:
    """Tests for _calculate_hash function."""
    ...

class TestBuildDataCheckString:
    """Tests for _build_data_check_string function."""
    ...

class TestValidateInitData:
    """Tests for validate_init_data function."""
    ...
```

---

## Порядок выполнения

1. **Конфиг** — добавить `init_data_expire_seconds` в Settings
2. **Exceptions** — создать `app/services/auth/exceptions.py`
3. **Schemas** — создать `app/api/schemas/auth.py` и `user.py`
4. **InitData Service** — создать `app/services/auth/init_data.py`
5. **Tests для InitData** — написать unit-тесты для валидации
6. **Dependencies** — создать `app/api/deps.py`
7. **Users Router** — создать `app/api/routes/users.py`
8. **App Factory** — создать `app/api/__init__.py`
9. **Integration Tests** — написать тесты для API endpoints
10. **Main Integration** — обновить `app/main.py`
11. **Self-Review** — прогнать чеклист из CLAUDE.md

---

## Безопасность

### Защита от атак

| Угроза | Защита |
|--------|--------|
| **Replay attack** | Проверка `auth_date` (default: 1 час) |
| **Signature forgery** | HMAC-SHA256 с bot token |
| **Token leakage** | Bot token хранится только на сервере |
| **Timing attack** | Использовать `hmac.compare_digest()` для сравнения хешей |

### Рекомендации

1. **Timing-safe сравнение** — использовать `hmac.compare_digest()` вместо `==`
2. **Логирование** — логировать неуспешные попытки аутентификации
3. **Rate limiting** — рассмотреть добавление в будущем (отдельная задача)

---

## Ограничения и допущения

1. **chat_id** — В контексте TMA используем `user.id` как `chat_id` (для отправки уведомлений)
2. **utm_source** — Пока не передаём (default: "direct"), можно расширить через `start_param`
3. **CORS** — Открыт для всех origins (TMA iframe)
4. **Rate limiting** — Не включено в этот план (отдельная задача)

---

## Источники

- [Telegram Core: Web Apps](https://core.telegram.org/bots/webapps#validating-data-received-via-the-web-app)
- [Telegram Mini Apps: Init Data](https://docs.telegram-mini-apps.com/platform/init-data)
- [Python HMAC-SHA256 Example](https://gist.github.com/Malith-Rukshan/da02bbf6e0219653c53ec9116cdd37f2)

---

## Checklist перед началом реализации

- [ ] План утверждён
- [ ] Bot token доступен в `.env`
- [ ] Понятен формат `Authorization: tma <initData>`
- [ ] Тестовые initData можно сгенерировать для unit-тестов
