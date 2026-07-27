# Фаза 1.1: База данных — SQLAlchemy модели

**Статус:** COMPLETED
**Зависимости:** нет
**Результат:** Полностью рабочий слой БД с моделями, сессиями и репозиториями

---

## Структура файлов

```
app/db/
├── __init__.py
├── base.py              # DeclarativeBase, общие миксины
├── session.py           # AsyncSession factory, get_session
├── enums.py             # Enum классы для статусов
├── models/
│   ├── __init__.py      # экспорт всех моделей
│   ├── user.py          # User
│   ├── payment.py       # Payment
│   ├── credit_package.py # CreditPackage
│   ├── transaction.py   # Transaction
│   ├── ai_model.py      # AIModel
│   ├── model_mode.py    # ModelMode
│   └── generation_job.py # GenerationJob
└── repositories/
    ├── __init__.py
    ├── base.py          # BaseRepository (generic CRUD)
    ├── user.py          # UserRepository
    └── generation.py    # GenerationJobRepository
```

---

## Шаги реализации

### Шаг 1: Base и Enums
**Файлы:** `base.py`, `enums.py`

```python
# enums.py
class PaymentStatus(str, Enum):
    pending = "pending"
    success = "success"
    failed = "failed"

class TransactionType(str, Enum):
    deposit = "deposit"      # пополнение
    withdrawal = "withdrawal" # списание за генерацию
    refund = "refund"        # возврат

class ContentType(str, Enum):
    image = "image"
    video = "video"

class JobStatus(str, Enum):
    queue = "queue"
    processing = "processing"
    done = "done"
    error = "error"
```

**Критерий готовности:** Enums импортируются без ошибок

---

### Шаг 2: Модели (по порядку зависимостей)

#### 2.1 User
- PK: `user_id` (Integer, autoincrement)
- `telegram_user_id` (BigInteger, unique, index) — Telegram ID может быть > 2^31
- `first_name`, `last_name`, `username` (String)
- `chat_id` (BigInteger)
- `utm_source` (String, default="direct")
- `created_at` (DateTime, server_default=now)

#### 2.2 CreditPackage
- PK: `id`
- `name`, `description` (String)
- `credit_amount`, `fiat_price` (Integer)
- `is_active` (Boolean, default=True)

#### 2.3 AIModel
- PK: `id`
- `name`, `description` (String)
- `type` (Enum: image/video)

#### 2.4 ModelMode
- PK: `id`
- FK: `model_id` → AIModel
- `name`, `description` (String)
- `price` (Integer) — стоимость в кредитах
- `config` (JSON)
- `is_active` (Boolean)

#### 2.5 Payment
- PK: `payment_id`
- FK: `user_id` → User
- `status` (Enum)
- `amount_currency` (Integer) — в копейках
- `created_at` (DateTime)
- `details` (JSON)

#### 2.6 GenerationJob
- PK: `job_id`
- FK: `user_id` → User
- FK: `model_mode_id` → ModelMode
- `status` (Enum)
- `provider_task_id` (String, nullable) — ID от kei.ai
- `provider_complete_time` (DateTime, nullable)
- `provider_consume_credit` (Integer, default=0)
- `cost_credit` (Integer)
- `created_at` (DateTime)
- `error` (Text, nullable)
- `prompt` (Text)
- `generation_params` (JSON)
- `references_meta` (JSON, nullable)
- `success_url_asset` (String, nullable)
- `telegram_file_id` (String, nullable)

#### 2.7 Transaction
- PK: `tx_id`
- FK: `user_id` → User
- `type` (Enum)
- `amount_credits` (Integer) — положительный для deposit, отрицательный для withdrawal
- `created_at` (DateTime)
- FK: `job_id` → GenerationJob (nullable)
- FK: `payment_id` → Payment (nullable)
- FK: `credit_package_id` → CreditPackage (nullable)

**Критерий готовности:** Все модели создаются, связи работают

---

### Шаг 3: Session Management
**Файл:** `session.py`

```python
# Async engine + sessionmaker
# get_session() — async context manager
# create_tables() — для создания таблиц (dev)
```

**Критерий готовности:** `async with get_session() as session` работает

---

### Шаг 4: Repositories (Порты и адаптеры)
**Файлы:** `repositories/`

Базовый репозиторий:
- `get_by_id(id)`
- `get_all(limit, offset)`
- `create(obj)`
- `update(obj)`
- `delete(id)`

UserRepository:
- `get_by_telegram_id(telegram_user_id)`
- `get_or_create(telegram_user_id, ...)`
- `get_balance(user_id)` — сумма транзакций

GenerationJobRepository:
- `get_user_jobs(user_id, limit)`
- `get_pending_jobs()` — для polling статусов

**Критерий готовности:** CRUD операции работают в тестах

---

### Шаг 5: Тесты
**Файлы:** `tests/test_db/`

- `test_models.py` — создание всех моделей
- `test_repositories.py` — CRUD операции
- `test_user_balance.py` — расчёт баланса через транзакции

**Критерий готовности:** `pytest tests/test_db/ -v` проходит

---

## Риски

1. **BigInteger для Telegram ID** — SQLite поддерживает, но проверить
2. **JSON поля в SQLite** — работает через `sqlalchemy.JSON`
3. **Enum в SQLite** — хранится как String, проверить миграции

---

## Стратегия отката

Все изменения в `app/db/` — можно откатить через git.
БД создаётся заново при тестировании (in-memory SQLite).

---

## Оценка

- Шаг 1 (base, enums): ~15 мин
- Шаг 2 (7 моделей): ~45 мин
- Шаг 3 (session): ~15 мин
- Шаг 4 (repositories): ~30 мин
- Шаг 5 (тесты): ~30 мин

**Итого:** ~2-2.5 часа
