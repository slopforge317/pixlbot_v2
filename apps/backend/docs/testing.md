# Testing Patterns and Fixtures

## Running Tests

```bash
# All tests
PYTHONPATH=app poetry run pytest -q

# Verbose output
PYTHONPATH=app poetry run pytest -v

# Single test file
PYTHONPATH=app poetry run pytest tests/test_db/test_models.py -v

# Single test function
PYTHONPATH=app poetry run pytest tests/test_db/test_models.py::test_create_user -v
```

## Test Structure

```
tests/
├── conftest.py                    # Global fixtures (anyio_backend)
├── test_config.py                 # Settings tests
├── test_api/
│   ├── conftest.py               # API fixtures (client, valid_init_data, seed_models)
│   ├── test_auth.py              # Authentication endpoint tests
│   ├── test_models.py            # AI model + tier hierarchy tests
│   ├── test_generations.py       # Generation CRUD tests
│   ├── test_packages.py          # Credit package tests
│   └── test_webhook.py           # Telegram webhook tests
├── test_bot/
│   ├── conftest.py               # Bot fixtures
│   ├── test_handlers.py          # Bot command tests
│   └── test_payments.py          # Invoice, checkout, and idempotency tests
├── test_db/
│   ├── conftest.py               # DB-specific fixtures (db_session)
│   ├── test_models.py            # ORM model tests
│   └── test_repositories.py      # Repository tests
└── test_services/
    ├── test_payment.py            # YooKassa receipt payload unit test
    ├── test_auth/
    │   └── test_init_data.py     # InitData validation unit tests
    ├── test_generation.py        # Generation service tests (build_context, error handling)
    └── test_kie/
        ├── test_schemas.py       # Pydantic schema tests
        ├── test_client.py        # HTTP client tests (mocked)
        └── test_service.py       # Service tests (mocked)
```

## Fixtures

### `anyio_backend` (global)
Returns `"asyncio"` for pytest-asyncio compatibility.

```python
@pytest.fixture
def anyio_backend():
    return "asyncio"
```

### `db_session` (test_db/conftest.py)
Creates PostgreSQL test database for each test:
1. Creates async engine with `TEST_DATABASE_URL` (PostgreSQL)
2. Creates all tables via `Base.metadata.create_all`
3. Yields async session
4. Drops all tables after test
5. Disposes engine

```python
@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # ... yield session ...
```

### `client` (test_api/conftest.py)
Creates httpx AsyncClient with FastAPI test app:
1. Connects to the isolated PostgreSQL test database
2. Creates all tables
3. Creates FastAPI app via `create_app()`
4. Overrides `get_db_session` dependency with test session maker
5. Yields httpx AsyncClient with ASGITransport
6. Drops all tables and disposes the engine

**Important:** Uses the same SQLAlchemy metadata and PostgreSQL dialect as
production. Start the isolated database with the root `scripts/test.ps1`.

### `valid_init_data` / `expired_init_data` (test_api/conftest.py)
Helper fixtures generating valid/expired Telegram InitData strings for testing authentication.

### `mock_client` (test_services/test_kie/)
MagicMock with `spec=KieClient` for testing KieService.

### `kie_service` (test_services/test_kie/)
KieService instance with mocked client and fast polling settings.

## Testing Patterns

### Model Tests
Direct SQLAlchemy operations to verify:
- Model creation with required fields
- Default values applied
- Relationships work correctly
- Enums serialize properly

```python
@pytest.mark.asyncio
async def test_create_user(db_session: AsyncSession) -> None:
    user = User(telegram_user_id=123, first_name="Test", chat_id=123)
    db_session.add(user)
    await db_session.flush()
    assert user.user_id is not None
```

### Repository Tests
Test repository methods with real (in-memory) database:
- CRUD operations
- Custom queries
- Edge cases (not found, duplicates)

```python
@pytest.mark.asyncio
async def test_user_get_or_create_new(db_session: AsyncSession) -> None:
    repo = UserRepository(db_session)
    user, created = await repo.get_or_create(...)
    assert created is True
```

### Service Tests (Mocked)
Test service logic with mocked HTTP client:
- Mock `create_task` and `get_task_status` responses
- Test polling behavior with `side_effect` for multiple calls
- Test timeout handling
- Test error handling

```python
@pytest.mark.asyncio
async def test_wait_for_result_polling(kie_service, mock_client):
    mock_client.get_task_status = AsyncMock(side_effect=[
        # First two calls: still generating
        TaskStatusResponse(..., state=KieTaskState.generating),
        TaskStatusResponse(..., state=KieTaskState.generating),
        # Third call: success
        TaskStatusResponse(..., state=KieTaskState.success),
    ])
    result = await kie_service.wait_for_result("task_123")
assert mock_client.get_task_status.call_count == 3
```

### Telegram Payments Tests
Payment tests use a real PostgreSQL test session and a mocked Telegram bot. They
verify that invoice creation requests and forwards email to YooKassa, produces
matching receipt totals, rejects checkout without email, marks invoice delivery
errors as failed, and grants credits only once for duplicate
`SuccessfulPayment` updates.

### Schema Tests
Test Pydantic model validation:
- Valid input accepted
- Helper methods work (e.g., `is_success()`, `get_result_urls()`)
- JSON parsing from API responses

### API Integration Tests
Test FastAPI endpoints with httpx AsyncClient:
- Mock `services.auth.init_data.settings` to control bot_token and expiration
- Generate valid/invalid initData using helper functions
- Verify HTTP status codes and response bodies

```python
@pytest.mark.asyncio
@patch("services.auth.init_data.settings")
async def test_valid_auth_returns_user(mock_settings, client, valid_init_data):
    mock_settings.bot_token = TEST_BOT_TOKEN
    mock_settings.init_data_expire_seconds = 3600

    response = await client.get(
        "/api/me",
        headers={"Authorization": f"tma {valid_init_data}"},
    )
    assert response.status_code == 200
    assert response.json()["telegram_user_id"] == 123456789
```

### InitData Validation Tests
Unit tests for `validate_init_data()` and helper functions:
- Test HMAC-SHA256 calculation
- Test data-check-string building
- Test various error conditions (expired, invalid hash, missing fields)

## Conventions

1. **Test function naming:** `test_<what>_<scenario>`
2. **One assertion focus:** Each test verifies one behavior
3. **Arrange-Act-Assert:** Setup → Execute → Verify
4. **No external dependencies:** All external services mocked
5. **Async tests:** Use `@pytest.mark.asyncio` decorator

## Mocking Guidelines

### HTTP Responses
```python
mock_response = MagicMock()
mock_response.status_code = 200
mock_response.json.return_value = {"code": 200, "data": {...}}
```

### Async Methods
```python
mock_client.create_task = AsyncMock(return_value=CreateTaskResponse(...))
```

### Multiple Calls
```python
mock_client.get_task_status = AsyncMock(side_effect=[
    response1, response2, response3
])
```
