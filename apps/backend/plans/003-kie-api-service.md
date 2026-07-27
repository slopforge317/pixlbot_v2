# Фаза 1.2: Сервис KIE API

**Статус:** COMPLETED
**Зависимости:** Фаза 1.1 (БД)
**Результат:** HTTP клиент для KIE API с поддержкой создания задач и polling статуса

---

## Ключевая информация из документации

### API
- **Base URL:** `https://api.kie.ai`
- **Auth:** `Authorization: Bearer <API_KEY>`
- **Content-Type:** `application/json`

### Endpoints
1. **Создание задачи:** `POST /api/v1/jobs/createTask`
2. **Статус задачи:** `GET /api/v1/jobs/recordInfo?taskId=xxx`

### Асинхронная модель
- Все генерации асинхронны
- HTTP 200 = задача создана (НЕ завершена)
- Получение результата: polling или callback URL

### Состояния задачи
| State | Описание | Действие |
|-------|----------|----------|
| `waiting` | В очереди | Продолжать polling |
| `queuing` | В очереди обработки | Продолжать polling |
| `generating` | Генерируется | Продолжать polling |
| `success` | Успешно | Парсить `resultJson` |
| `fail` | Ошибка | Читать `failCode`, `failMsg` |

### Rate Limits
- 20 запросов / 10 секунд на создание
- 10 запросов / секунду на polling
- HTTP 429 при превышении

### Хранение результатов
- Медиа-файлы: 14 дней
- URL результатов: ~24 часа (нужно скачивать)

---

## Структура файлов

```
app/services/
├── __init__.py
├── kie/
│   ├── __init__.py
│   ├── client.py        # HTTP клиент (httpx)
│   ├── schemas.py       # Pydantic модели запросов/ответов
│   ├── enums.py         # TaskState enum
│   ├── exceptions.py    # Кастомные исключения
│   └── service.py       # Высокоуровневый сервис
```

---

## Шаги реализации

### Шаг 1: Enums и Exceptions
**Файлы:** `enums.py`, `exceptions.py`

```python
# enums.py
class KieTaskState(str, Enum):
    waiting = "waiting"
    queuing = "queuing"
    generating = "generating"
    success = "success"
    fail = "fail"

# exceptions.py
class KieAPIError(Exception): ...
class KieAuthError(KieAPIError): ...      # 401
class KieInsufficientCredits(KieAPIError): ...  # 402
class KieRateLimitError(KieAPIError): ...  # 429
class KieTaskFailedError(KieAPIError): ... # task state = fail
```

**Критерий готовности:** Enums и exceptions импортируются

---

### Шаг 2: Pydantic Schemas
**Файл:** `schemas.py`

```python
# Запрос на создание задачи
class CreateTaskRequest(BaseModel):
    model: str
    callBackUrl: str | None = None
    input: dict[str, Any]

# Ответ создания задачи
class CreateTaskResponse(BaseModel):
    code: int
    msg: str
    data: TaskData | None

class TaskData(BaseModel):
    taskId: str

# Ответ статуса задачи
class TaskStatusResponse(BaseModel):
    code: int
    message: str
    data: TaskStatusData | None

class TaskStatusData(BaseModel):
    taskId: str
    model: str
    state: KieTaskState
    param: str  # JSON string
    resultJson: str  # JSON string с resultUrls
    failCode: str
    failMsg: str
    completeTime: int | None
    createTime: int
    updateTime: int

# Результат генерации (парсится из resultJson)
class GenerationResult(BaseModel):
    resultUrls: list[str]
```

**Критерий готовности:** Schemas валидируют JSON из документации

---

### Шаг 3: HTTP Client
**Файл:** `client.py`

```python
class KieClient:
    def __init__(self, api_key: str, base_url: str = "https://api.kie.ai"):
        self.client = httpx.AsyncClient(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30.0,
        )

    async def create_task(self, request: CreateTaskRequest) -> CreateTaskResponse
    async def get_task_status(self, task_id: str) -> TaskStatusResponse
    async def close(self)
```

Обработка ошибок:
- 401 → `KieAuthError`
- 402 → `KieInsufficientCredits`
- 429 → `KieRateLimitError`
- 5xx → `KieAPIError`

**Критерий готовности:** Клиент делает запросы к API

---

### Шаг 4: High-Level Service
**Файл:** `service.py`

```python
class KieService:
    def __init__(self, client: KieClient):
        self.client = client

    async def create_generation(
        self,
        model: str,
        prompt: str,
        image_urls: list[str] | None = None,
        aspect_ratio: str = "1:1",
        quality: str = "basic",
        callback_url: str | None = None,
    ) -> str:
        """Создать задачу генерации, вернуть task_id."""

    async def get_result(self, task_id: str) -> GenerationResult | None:
        """Получить результат задачи (None если ещё не готово)."""

    async def wait_for_result(
        self,
        task_id: str,
        timeout: float = 300,
        poll_interval: float = 3.0,
    ) -> GenerationResult:
        """Polling до получения результата или таймаута."""

    def is_terminal_state(self, state: KieTaskState) -> bool:
        """Проверить, завершена ли задача."""
```

**Критерий готовности:** Сервис создаёт задачи и получает результаты

---

### Шаг 5: Интеграция с конфигом
**Файл:** `app/core/config.py` (обновить)

```python
class Settings(BaseSettings):
    # ... existing ...
    kie_api_key: str = ""
    kie_api_base_url: str = "https://api.kie.ai"
    kie_poll_interval: float = 3.0
    kie_poll_timeout: float = 300.0
```

---

### Шаг 6: Тесты
**Файлы:** `tests/test_services/test_kie/`

- `test_schemas.py` — валидация моделей
- `test_client.py` — мок HTTP запросов
- `test_service.py` — интеграционные тесты с моками

**Критерий готовности:** `pytest tests/test_services/ -v` проходит

---

## Модели для генерации (из документации)

| Model | Тип | Endpoint model value |
|-------|-----|---------------------|
| Seedream 4.5 Edit | image | `seedream/4.5-edit` |
| Grok Imagine | image | `grok-imagine/text-to-image` |
| Kling | video | `kling-1.0` |

*Полный список: https://kie.ai/market*

---

## Риски

1. **Rate Limits** — нужен retry с exponential backoff
2. **Долгие генерации** — видео может генерироваться 5+ минут
3. **Callback vs Polling** — начнём с polling, callback позже
4. **URL expiration** — результаты живут 24ч, нужно сохранять в Telegram

---

## Стратегия отката

Все изменения в `app/services/kie/` — можно откатить через git.
Тесты используют моки, не требуют реального API.

---

## Оценка

- Шаг 1 (enums, exceptions): ~10 мин
- Шаг 2 (schemas): ~20 мин
- Шаг 3 (client): ~30 мин
- Шаг 4 (service): ~30 мин
- Шаг 5 (config): ~5 мин
- Шаг 6 (тесты): ~30 мин

**Итого:** ~2 часа
