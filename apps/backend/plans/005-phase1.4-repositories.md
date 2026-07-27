# План: Фаза 1.4 — Недостающие Repositories

**Статус:** DONE
**Цель:** Реализовать недостающие репозитории для работы с AI моделями, режимами, пакетами кредитов и транзакциями.

---

## Контекст

Существующие репозитории следуют паттерну:
- Наследование от `BaseRepository[ModelT]`
- CRUD из базового класса: `get_by_id()`, `get_all()`, `create()`, `update()`, `delete()`
- Специфичные методы в дочернем классе
- Async/await с SQLAlchemy 2.0 select API

---

## Задачи

### 1. AiModelRepository

**Файл:** `app/db/repositories/ai_model.py`

**Методы:**
| Метод | Описание |
|-------|----------|
| `get_all_with_modes()` | Получить все модели с активными режимами (eager load) |
| `get_by_type(type: ContentType)` | Фильтр моделей по типу (image/video) |
| `get_with_modes(id: int)` | Получить модель с режимами по ID |

**Реализация:**
```python
class AiModelRepository(BaseRepository[AIModel]):
    model = AIModel

    async def get_all_with_modes(self) -> list[AIModel]:
        """Get all models with their active modes."""
        stmt = (
            select(AIModel)
            .options(selectinload(AIModel.modes.and_(ModelMode.is_active == True)))
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().unique().all())

    async def get_by_type(self, content_type: ContentType) -> list[AIModel]:
        """Get models by content type (image/video)."""
        stmt = select(AIModel).where(AIModel.type == content_type)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_with_modes(self, model_id: int) -> AIModel | None:
        """Get model by ID with its modes."""
        stmt = (
            select(AIModel)
            .where(AIModel.id == model_id)
            .options(selectinload(AIModel.modes))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
```

---

### 2. ModelModeRepository

**Файл:** `app/db/repositories/model_mode.py`

**Методы:**
| Метод | Описание |
|-------|----------|
| `get_active()` | Получить все активные режимы |
| `get_by_model_id(model_id: int)` | Получить режимы для конкретной модели |
| `get_active_by_model_id(model_id: int)` | Получить активные режимы для модели |

**Реализация:**
```python
class ModelModeRepository(BaseRepository[ModelMode]):
    model = ModelMode

    async def get_active(self, limit: int = 100, offset: int = 0) -> list[ModelMode]:
        """Get all active modes."""
        stmt = (
            select(ModelMode)
            .where(ModelMode.is_active == True)
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_model_id(self, model_id: int) -> list[ModelMode]:
        """Get all modes for a specific model."""
        stmt = select(ModelMode).where(ModelMode.model_id == model_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_active_by_model_id(self, model_id: int) -> list[ModelMode]:
        """Get active modes for a specific model."""
        stmt = (
            select(ModelMode)
            .where(ModelMode.model_id == model_id, ModelMode.is_active == True)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
```

---

### 3. CreditPackageRepository

**Файл:** `app/db/repositories/credit_package.py`

**Методы:**
| Метод | Описание |
|-------|----------|
| `get_active()` | Получить все активные пакеты |
| `get_active_ordered_by_price()` | Активные пакеты, отсортированные по цене |

**Реализация:**
```python
class CreditPackageRepository(BaseRepository[CreditPackage]):
    model = CreditPackage

    async def get_active(self, limit: int = 100, offset: int = 0) -> list[CreditPackage]:
        """Get all active credit packages."""
        stmt = (
            select(CreditPackage)
            .where(CreditPackage.is_active == True)
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_active_ordered_by_price(self) -> list[CreditPackage]:
        """Get active packages ordered by price ascending."""
        stmt = (
            select(CreditPackage)
            .where(CreditPackage.is_active == True)
            .order_by(CreditPackage.fiat_price.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
```

---

### 4. TransactionRepository

**Файл:** `app/db/repositories/transaction.py`

**Методы:**
| Метод | Описание |
|-------|----------|
| `get_user_transactions(user_id, limit, offset)` | История транзакций пользователя с пагинацией |
| `get_by_type(user_id, type)` | Фильтр по типу транзакции |
| `create_deposit(...)` | Создание транзакции депозита |
| `create_withdrawal(...)` | Создание транзакции списания |
| `create_refund(...)` | Создание транзакции возврата |

**Важно:** Transactions — immutable ledger, методы `update()` и `delete()` не должны использоваться.

**Реализация:**
```python
class TransactionRepository(BaseRepository[Transaction]):
    model = Transaction

    async def get_user_transactions(
        self, user_id: int, limit: int = 50, offset: int = 0
    ) -> list[Transaction]:
        """Get user's transaction history, newest first."""
        stmt = (
            select(Transaction)
            .where(Transaction.user_id == user_id)
            .order_by(Transaction.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_type(
        self, user_id: int, tx_type: TransactionType
    ) -> list[Transaction]:
        """Get user's transactions filtered by type."""
        stmt = (
            select(Transaction)
            .where(Transaction.user_id == user_id, Transaction.type == tx_type)
            .order_by(Transaction.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create_deposit(
        self,
        user_id: int,
        amount_credits: int,
        payment_id: int | None = None,
        credit_package_id: int | None = None,
    ) -> Transaction:
        """Create a deposit (credit purchase) transaction."""
        return await self.create(
            user_id=user_id,
            type=TransactionType.deposit,
            amount_credits=amount_credits,
            payment_id=payment_id,
            credit_package_id=credit_package_id,
        )

    async def create_withdrawal(
        self,
        user_id: int,
        amount_credits: int,
        job_id: int,
    ) -> Transaction:
        """Create a withdrawal (generation charge) transaction.

        Note: amount_credits should be negative.
        """
        return await self.create(
            user_id=user_id,
            type=TransactionType.withdrawal,
            amount_credits=-abs(amount_credits),  # Ensure negative
            job_id=job_id,
        )

    async def create_refund(
        self,
        user_id: int,
        amount_credits: int,
        job_id: int,
    ) -> Transaction:
        """Create a refund transaction (e.g., failed generation)."""
        return await self.create(
            user_id=user_id,
            type=TransactionType.refund,
            amount_credits=abs(amount_credits),  # Ensure positive
            job_id=job_id,
        )
```

---

## Порядок выполнения

1. **Создание репозиториев** (4 файла)
   - `app/db/repositories/ai_model.py`
   - `app/db/repositories/model_mode.py`
   - `app/db/repositories/credit_package.py`
   - `app/db/repositories/transaction.py`

2. **Обновление экспортов**
   - `app/db/repositories/__init__.py` — добавить новые репозитории

3. **Тесты** (добавить в `tests/test_db/test_repositories.py`)
   - Тесты для `AiModelRepository`
   - Тесты для `ModelModeRepository`
   - Тесты для `CreditPackageRepository`
   - Тесты для `TransactionRepository`

4. **Проверка качества**
   - `isort`, `black`, `flake8`, `pyright`
   - Запуск тестов

5. **Обновление документации**
   - `docs/structure.md` — добавить описание новых репозиториев
   - `docs/test-summary.md` — обновить информацию о тестах

---

## Тест-кейсы

### AiModelRepository
- `test_ai_model_get_all_with_modes` — получение всех моделей с режимами
- `test_ai_model_get_by_type` — фильтрация по типу
- `test_ai_model_get_with_modes` — получение одной модели с режимами

### ModelModeRepository
- `test_model_mode_get_active` — получение только активных режимов
- `test_model_mode_get_by_model_id` — фильтрация по модели
- `test_model_mode_get_active_by_model_id` — активные режимы для модели

### CreditPackageRepository
- `test_credit_package_get_active` — получение активных пакетов
- `test_credit_package_get_active_ordered_by_price` — сортировка по цене

### TransactionRepository
- `test_transaction_get_user_transactions` — история с пагинацией
- `test_transaction_get_by_type` — фильтрация по типу
- `test_transaction_create_deposit` — создание депозита
- `test_transaction_create_withdrawal` — создание списания
- `test_transaction_create_refund` — создание возврата

---

## Риски

1. **Eager loading в SQLAlchemy** — нужно убедиться, что `selectinload` корректно работает с условиями фильтрации режимов
2. **Negative amounts** — важно правильно обрабатывать знак в транзакциях списания

---

## Rollback

При необходимости откатить:
```bash
git checkout HEAD -- app/db/repositories/
git checkout HEAD -- tests/test_db/test_repositories.py
```

---

## Acceptance Criteria

- [x] Все 4 репозитория созданы и работают
- [x] Все тесты проходят (59 passed)
- [x] Код соответствует стилю проекта (isort, black, flake8, pyright)
- [x] Документация обновлена
