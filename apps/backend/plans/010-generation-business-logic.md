# План 010: Генерация — бизнес-логика

**Статус:** DONE
**Roadmap:** 2.6 Генерация — бизнес-логика
**Зависимости:**
- POST /api/generations (готов — создание job, списание кредитов)
- KIE API service (готов — services/kie/)
- GenerationJobRepository (готов)
- TransactionRepository (готов — включая create_refund)
- Telegram Bot (готов — базовые команды)

---

## Цель

Реализовать полный цикл обработки генерации:
1. Отправка задачи в KIE API после создания job
2. Background polling статуса
3. Обновление GenerationJob при завершении
4. Отправка результата пользователю через бота
5. Возврат кредитов при ошибке

---

## Текущее состояние

**Что уже работает:**
- ✅ POST /api/generations — создаёт job, списывает кредиты
- ✅ KieService — create_generation(), wait_for_result(), polling
- ✅ TransactionRepository — create_withdrawal(), create_refund()
- ✅ Bot — send_photo(), send_video(), send_message()

**Что НЕ работает (КРИТИЧНО):**
- ❌ process_generation() — функция не существует
- ❌ Интеграция KIE API в flow — не вызывается
- ❌ Обновление job.status — остаётся "queue" навсегда
- ❌ Уведомления в бот — не отправляются
- ❌ Refund при ошибке — метод есть, но не вызывается

---

## Компоненты для реализации

### 1. GenerationService (`app/services/generation.py`)

**Основная функция:**

```python
async def process_generation(
    job_id: int,
    session: AsyncSession,
    bot: Bot,
) -> None:
    """
    Обработать задачу генерации:
    1. Отправить в KIE API
    2. Дождаться результата (polling)
    3. Обновить job в БД
    4. Отправить уведомление в бот
    5. При ошибке — вернуть кредиты
    """
```

**Алгоритм:**

```
1. Получить GenerationJob из БД (с mode и model)
2. Получить User (для chat_id)
3. Извлечь конфиг из mode.provider_config:
   - kie_model: str (название модели в KIE)
   - kie_params: dict (дополнительные параметры)
4. Обновить job.status = processing
5. Отправить в KIE API:
   - model = mode.provider_config["kie_model"]
   - prompt = job.prompt
   - negative_prompt = job.generation_params.get("negative_prompt")
   - seed = job.generation_params.get("seed")
6. Сохранить job.provider_task_id = kie_task_id
7. Ожидать результата (KieService.wait_for_result):
   - Polling каждые 3-15 сек (адаптивно)
   - Таймаут: 5 минут
8. При успехе:
   a. job.status = done
   b. job.success_url_asset = result.result_urls[0]
   c. job.provider_complete_time = now()
   d. Отправить фото/видео в бот
   e. Сохранить telegram_file_id
9. При ошибке:
   a. job.status = error
   b. job.error = error_message
   c. Создать refund транзакцию
   d. Отправить уведомление об ошибке в бот
```

---

### 2. NotificationService (`app/services/notification.py`)

**Функции:**

```python
async def send_generation_result(
    bot: Bot,
    chat_id: int,
    result_url: str,
    is_video: bool = False,
) -> str | None:
    """
    Отправить результат генерации пользователю.
    Возвращает telegram_file_id для кеширования.
    """

async def send_generation_error(
    bot: Bot,
    chat_id: int,
    error_message: str,
    credits_refunded: int,
) -> None:
    """Уведомить об ошибке и возврате кредитов."""

async def send_payment_success(
    bot: Bot,
    chat_id: int,
    credits_added: int,
    new_balance: int,
) -> None:
    """Уведомить об успешном пополнении баланса."""
```

---

### 3. Интеграция в API endpoint

**Файл:** `app/api/routes/generations.py`

**Изменение:**

```python
# Строка 76-77 (сейчас закомментировано)
# Было:
# background_tasks.add_task(process_generation, job.job_id)
# AICODE-TODO: Implement process_generation in services/generation.py

# Станет:
from services.generation import process_generation
background_tasks.add_task(
    process_generation,
    job_id=job.job_id,
    session=session,  # Новая сессия будет создана внутри
    bot=bot,  # Инжектить через dependency
)
```

**Проблема:** Background task нужна отдельная DB сессия (текущая закроется после response).

**Решение:**
```python
async def process_generation(job_id: int) -> None:
    """Entry point для background task."""
    async with async_session_factory() as session:
        bot = create_bot()
        await _process_generation_impl(job_id, session, bot)
```

---

### 4. Обработка ошибок

**KIE API ошибки:**

| Exception | Действие |
|-----------|----------|
| `KieTaskFailedError` | Refund + error notification |
| `KieTaskTimeoutError` | Refund + error notification |
| `KieInsufficientCreditsError` | Refund + error notification (наш баланс в KIE) |
| `KieRateLimitError` | Retry после паузы (429) |
| `KieAPIError` (general) | Refund + error notification |

**Refund логика:**

```python
async def refund_credits(
    session: AsyncSession,
    user_id: int,
    job_id: int,
    amount: int,
) -> None:
    """Вернуть кредиты пользователю."""
    tx_repo = TransactionRepository(session)
    await tx_repo.create_refund(
        user_id=user_id,
        amount_credits=amount,
        job_id=job_id,
    )
```

---

### 5. Определение типа медиа (фото/видео)

**Из mode.provider_config:**

```python
# Пример provider_config для режима
{
    "kie_model": "stable-diffusion-xl",
    "kie_params": {"steps": 30},
    "media_type": "image"  # или "video"
}
```

**Логика:**

```python
media_type = mode.provider_config.get("media_type", "image")
if media_type == "video":
    await notification.send_video(...)
else:
    await notification.send_photo(...)
```

---

## Файлы для создания/изменения

### Создать:

1. **`app/services/generation.py`**
   - `process_generation()` — основная функция
   - `_process_generation_impl()` — реализация
   - `refund_credits()` — возврат кредитов

2. **`app/services/notification.py`**
   - `send_generation_result()` — отправка медиа
   - `send_generation_error()` — уведомление об ошибке
   - `send_payment_success()` — уведомление о платеже (для будущего)

### Изменить:

1. **`app/api/routes/generations.py`**
   - Раскомментировать и доработать background_tasks.add_task()
   - Добавить dependency для Bot (если нужно)

2. **`app/api/deps.py`** (опционально)
   - Добавить `get_bot()` dependency

---

## Pydantic Schemas (дополнения)

**Файл:** `app/services/generation.py` (внутренние типы)

```python
from dataclasses import dataclass

@dataclass
class GenerationContext:
    """Контекст для обработки генерации."""
    job: GenerationJob
    user: User
    mode: ModelMode
    model: AiModel
    kie_model: str
    kie_params: dict
    media_type: str  # "image" | "video"
```

---

## Тексты для бота

**Файл:** `app/bot/texts.py` (дополнения)

```python
# Generation notifications
GENERATION_SUCCESS = "✅ Ваша генерация готова!"
GENERATION_ERROR = (
    "❌ К сожалению, генерация не удалась.\n\n"
    "Причина: {error}\n\n"
    "💳 Кредиты возвращены: {credits}"
)
GENERATION_TIMEOUT = (
    "⏱ Генерация заняла слишком много времени.\n\n"
    "💳 Кредиты возвращены: {credits}"
)
```

---

## Шаги реализации

1. **Создать `app/services/notification.py`**
   - send_generation_result()
   - send_generation_error()

2. **Создать `app/services/generation.py`**
   - process_generation() с полной логикой
   - Интеграция с KieService
   - Обработка всех ошибок
   - Refund при неудаче

3. **Обновить тексты бота** `app/bot/texts.py`
   - Добавить шаблоны уведомлений

4. **Интегрировать в API** `app/api/routes/generations.py`
   - Раскомментировать background_tasks.add_task()
   - Передать необходимые зависимости

5. **Написать тесты** `tests/test_services/test_generation.py`
   - Успешная генерация (mock KIE)
   - Ошибка KIE → refund
   - Таймаут → refund
   - Уведомления отправляются

6. **Проверить** — isort, black, flake8, pyright, pytest

---

## Диаграмма потока

```
POST /api/generations
    │
    ├─ 1. Валидация mode ✅
    ├─ 2. Проверка баланса ✅
    ├─ 3. Создание GenerationJob ✅
    ├─ 4. Списание кредитов ✅
    ├─ 5. Запуск background task → [NEW]
    │       │
    │       ▼
    │   process_generation(job_id)
    │       ├─ 6. Получить job, user, mode
    │       ├─ 7. job.status = processing
    │       ├─ 8. KieService.create_generation()
    │       ├─ 9. Сохранить provider_task_id
    │       ├─ 10. KieService.wait_for_result()
    │       │       └─ Polling каждые 3-15 сек
    │       │
    │       ├─ [SUCCESS]
    │       │   ├─ 11. job.status = done
    │       │   ├─ 12. job.success_url_asset = url
    │       │   ├─ 13. send_generation_result()
    │       │   └─ 14. Сохранить telegram_file_id
    │       │
    │       └─ [ERROR]
    │           ├─ 11. job.status = error
    │           ├─ 12. job.error = message
    │           ├─ 13. create_refund()
    │           └─ 14. send_generation_error()
    │
    └─ 6. Вернуть response (job_id, status=queue) ✅
```

---

## Риски и митигация

| Риск | Митигация |
|------|-----------|
| Background task потеряется при рестарте | Добавить periodic job checker (cron) для "зависших" задач |
| KIE API недоступен | Retry с exponential backoff (уже в KieService) |
| Долгий polling блокирует workers | Limit concurrent tasks, async I/O |
| Telegram API rate limits | Retry с паузой, очередь уведомлений |
| DB сессия закрывается | Создавать новую сессию в background task |

---

## Тесты

**Файл:** `tests/test_services/test_generation.py`

1. **test_process_generation_success**
   - Mock KieService.generate_and_wait() → success
   - Проверить job.status == done
   - Проверить job.success_url_asset заполнен
   - Проверить bot.send_photo вызван

2. **test_process_generation_kie_error**
   - Mock KieService → KieTaskFailedError
   - Проверить job.status == error
   - Проверить refund транзакция создана
   - Проверить bot.send_message вызван с ошибкой

3. **test_process_generation_timeout**
   - Mock KieService → KieTaskTimeoutError
   - Проверить refund
   - Проверить уведомление

4. **test_notification_send_photo**
   - Mock Bot.send_photo()
   - Проверить возврат file_id

5. **test_notification_send_video**
   - Mock Bot.send_video()
   - Проверить возврат file_id

---

## Definition of Done

- [x] Создан `services/notification.py` с функциями отправки
- [x] Создан `services/generation.py` с process_generation()
- [x] Интегрирован background task в POST /api/generations
- [x] Обновлены тексты бота
- [x] Тесты написаны и проходят (13 тестов)
- [x] Код проверен (isort, black, flake8, pyright)
- [ ] E2E проверка: создать генерацию → получить результат в Telegram

---

## Верификация

1. **Запустить бота и API:**
   ```bash
   PYTHONPATH=app poetry run python -m bot
   PYTHONPATH=app poetry run uvicorn app.main:app --reload
   ```

2. **Создать генерацию через API:**
   ```bash
   curl -X POST http://localhost:8000/api/generations \
     -H "Authorization: ..." \
     -H "Content-Type: application/json" \
     -d '{"mode_id": 1, "prompt": "A sunset"}'
   ```

3. **Проверить:**
   - Job создан (status=queue)
   - Через 10-30 сек статус меняется на processing
   - При завершении — получить сообщение в Telegram
   - При ошибке — получить уведомление + проверить refund в transactions

4. **Тесты:**
   ```bash
   PYTHONPATH=app poetry run pytest tests/test_services/test_generation.py -v
   ```
