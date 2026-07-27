# План 008: API эндпоинты — Генерация

**Статус:** DONE
**Roadmap:** 2.4 API эндпоинты — Генерация
**Зависимости:**
- GenerationJobRepository (готов)
- TransactionRepository (готов)
- ModelModeRepository (готов)
- KIE API client (готов — services/kie/)
- Credit service (НЕ готов — нужен для 2.6, но базовую логику встроим)

---

## Цель

Реализовать эндпоинты для создания и отслеживания генераций изображений/видео.

---

## Эндпоинты

### POST /api/generations

**Описание:** Создание новой генерации

**Auth:** Required

**Request body:**
```json
{
  "mode_id": 1,
  "prompt": "A beautiful sunset over mountains",
  "negative_prompt": "blurry, low quality",
  "params": {
    "seed": 12345,
    "aspect_ratio": "16:9"
  }
}
```

**Response:** `201 Created`
```json
{
  "job_id": "uuid-string",
  "status": "queue",
  "mode_id": 1,
  "cost_credit": 10,
  "prompt": "A beautiful sunset over mountains",
  "created_at": "2024-01-15T12:00:00Z"
}
```

**Response:** `400 Bad Request` — недостаточно кредитов
```json
{
  "detail": "Insufficient credits",
  "balance": 5,
  "required": 10
}
```

**Response:** `404 Not Found` — mode не найден или неактивен

**Логика:**
1. Валидация `mode_id` — существует и `is_active=True`
2. Получить цену из `ModelMode.price`
3. Проверить баланс пользователя `UserRepository.get_balance()`
4. Если баланс < price → 400 с деталями
5. Создать `GenerationJob` со статусом `queue`
6. Списать кредиты через `TransactionRepository.create_withdrawal()`
7. Отправить задачу в KIE API (async background task)
8. Вернуть созданный job

**Background task:**
- Отправка в KIE API
- Polling статуса (отдельный сервис)
- При завершении: обновить job, отправить уведомление в бот
- При ошибке: refund кредитов

---

### GET /api/generations

**Описание:** История генераций пользователя

**Auth:** Required

**Query params:**
- `limit` (optional, default=10, max=50): количество записей
- `offset` (optional, default=0): смещение для пагинации
- `status` (optional): фильтр по статусу (`queue`, `processing`, `done`, `error`)

**Response:** `200 OK`
```json
{
  "generations": [
    {
      "job_id": "uuid-1",
      "status": "done",
      "mode_id": 1,
      "mode_name": "Standard",
      "model_name": "Stable Diffusion XL",
      "cost_credit": 10,
      "prompt": "A sunset...",
      "result_url": "https://...",
      "created_at": "2024-01-15T12:00:00Z"
    }
  ],
  "total": 42,
  "limit": 10,
  "offset": 0
}
```

**Логика:**
1. Вызвать `GenerationJobRepository.get_user_jobs(user_id, limit, offset)`
2. Опционально фильтровать по статусу
3. Подсчитать total для пагинации
4. Вернуть список с метаданными пагинации

---

### GET /api/generations/{job_id}

**Описание:** Статус и детали одной генерации

**Auth:** Required

**Path params:**
- `job_id`: UUID строка

**Response:** `200 OK`
```json
{
  "job_id": "uuid-string",
  "status": "done",
  "mode_id": 1,
  "mode_name": "Standard",
  "model_name": "Stable Diffusion XL",
  "cost_credit": 10,
  "prompt": "A sunset...",
  "negative_prompt": "blurry",
  "params": {"seed": 12345},
  "result_url": "https://...",
  "error_message": null,
  "created_at": "2024-01-15T12:00:00Z",
  "completed_at": "2024-01-15T12:01:30Z"
}
```

**Response:** `404 Not Found` — job не найден или принадлежит другому пользователю

**Логика:**
1. Получить job по `job_id`
2. Проверить `job.user_id == user.user_id`
3. Если не найден или чужой → 404
4. Вернуть детали

---

## Pydantic Schemas

**Файл:** `app/api/schemas/generation.py`

```python
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from db.enums import JobStatus


class GenerationCreateRequest(BaseModel):
    """Запрос на создание генерации."""

    mode_id: int
    prompt: str = Field(..., min_length=1, max_length=2000)
    negative_prompt: str | None = Field(None, max_length=1000)
    params: dict | None = None  # seed, aspect_ratio, etc.


class GenerationResponse(BaseModel):
    """Генерация (базовый response)."""

    job_id: UUID
    status: JobStatus
    mode_id: int
    cost_credit: int
    prompt: str
    created_at: datetime

    model_config = {"from_attributes": True}


class GenerationDetailResponse(GenerationResponse):
    """Генерация с полными деталями."""

    mode_name: str | None = None
    model_name: str | None = None
    negative_prompt: str | None = None
    params: dict | None = None
    result_url: str | None = None  # success_url_asset
    error_message: str | None = None
    completed_at: datetime | None = None


class GenerationListResponse(BaseModel):
    """Список генераций с пагинацией."""

    generations: list[GenerationDetailResponse]
    total: int
    limit: int
    offset: int


class InsufficientCreditsError(BaseModel):
    """Ошибка недостатка кредитов."""

    detail: str = "Insufficient credits"
    balance: int
    required: int
```

---

## Route Handler

**Файл:** `app/api/routes/generations.py`

```python
"""Generation API endpoints."""

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

from api.deps import CurrentUser, DBSession
from api.schemas.generation import (
    GenerationCreateRequest,
    GenerationDetailResponse,
    GenerationListResponse,
    GenerationResponse,
)
from db.enums import JobStatus
from db.repositories.generation_job import GenerationJobRepository
from db.repositories.model_mode import ModelModeRepository
from db.repositories.transaction import TransactionRepository
from db.repositories.user import UserRepository

router = APIRouter(prefix="/api", tags=["generations"])


@router.post("/generations", response_model=GenerationResponse, status_code=201)
async def create_generation(
    request: GenerationCreateRequest,
    user: CurrentUser,
    session: DBSession,
    background_tasks: BackgroundTasks,
) -> GenerationResponse:
    """
    Create a new generation job.

    Checks balance, deducts credits, and queues the job.
    """
    # 1. Validate mode exists and is active
    mode_repo = ModelModeRepository(session)
    mode = await mode_repo.get_by_id(request.mode_id)

    if not mode or not mode.is_active:
        raise HTTPException(status_code=404, detail="Mode not found or inactive")

    # 2. Check user balance
    user_repo = UserRepository(session)
    balance = await user_repo.get_balance(user.user_id)

    if balance < mode.price:
        raise HTTPException(
            status_code=400,
            detail={
                "detail": "Insufficient credits",
                "balance": balance,
                "required": mode.price,
            },
        )

    # 3. Create generation job
    job_repo = GenerationJobRepository(session)
    job = await job_repo.create(
        user_id=user.user_id,
        model_mode_id=mode.id,
        status=JobStatus.queue,
        cost_credit=mode.price,
        prompt=request.prompt,
        generation_params={
            "negative_prompt": request.negative_prompt,
            **(request.params or {}),
        },
    )

    # 4. Deduct credits
    tx_repo = TransactionRepository(session)
    await tx_repo.create_withdrawal(
        user_id=user.user_id,
        amount_credits=mode.price,
        job_id=job.job_id,
    )

    # 5. Queue background task for KIE API
    # background_tasks.add_task(process_generation, job.job_id)
    # AICODE-TODO: Implement process_generation in services/generation.py

    return GenerationResponse.model_validate(job)


@router.get("/generations", response_model=GenerationListResponse)
async def list_generations(
    user: CurrentUser,
    session: DBSession,
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0),
    status: JobStatus | None = Query(None),
) -> GenerationListResponse:
    """Get user's generation history with pagination."""
    job_repo = GenerationJobRepository(session)

    # Get jobs (filtered by status if provided)
    jobs = await job_repo.get_user_jobs(user.user_id, limit=limit, offset=offset)

    if status:
        jobs = [j for j in jobs if j.status == status]

    # AICODE-TODO: Add get_user_jobs_count() to repository for accurate total
    total = len(jobs)  # Temporary, should be separate count query

    generations = []
    for job in jobs:
        gen = GenerationDetailResponse(
            job_id=job.job_id,
            status=job.status,
            mode_id=job.model_mode_id,
            cost_credit=job.cost_credit,
            prompt=job.prompt,
            created_at=job.created_at,
            mode_name=job.model_mode.name if job.model_mode else None,
            model_name=job.model_mode.model.name if job.model_mode and job.model_mode.model else None,
            result_url=job.success_url_asset,
            params=job.generation_params,
        )
        generations.append(gen)

    return GenerationListResponse(
        generations=generations,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/generations/{job_id}", response_model=GenerationDetailResponse)
async def get_generation(
    job_id: UUID,
    user: CurrentUser,
    session: DBSession,
) -> GenerationDetailResponse:
    """Get details of a specific generation job."""
    job_repo = GenerationJobRepository(session)
    job = await job_repo.get_by_id(job_id)

    if not job or job.user_id != user.user_id:
        raise HTTPException(status_code=404, detail="Generation not found")

    return GenerationDetailResponse(
        job_id=job.job_id,
        status=job.status,
        mode_id=job.model_mode_id,
        cost_credit=job.cost_credit,
        prompt=job.prompt,
        created_at=job.created_at,
        mode_name=job.model_mode.name if job.model_mode else None,
        model_name=job.model_mode.model.name if job.model_mode and job.model_mode.model else None,
        negative_prompt=job.generation_params.get("negative_prompt") if job.generation_params else None,
        params=job.generation_params,
        result_url=job.success_url_asset,
    )
```

---

## Изменения в репозиториях

### GenerationJobRepository

Добавить методы:

```python
async def get_user_jobs_count(self, user_id: int, status: JobStatus | None = None) -> int:
    """Count user's jobs, optionally filtered by status."""
    query = select(func.count()).where(GenerationJob.user_id == user_id)
    if status:
        query = query.where(GenerationJob.status == status)
    result = await self.session.execute(query)
    return result.scalar() or 0

async def get_user_jobs_filtered(
    self,
    user_id: int,
    status: JobStatus | None = None,
    limit: int = 10,
    offset: int = 0,
) -> list[GenerationJob]:
    """Get user's jobs with optional status filter."""
    query = (
        select(GenerationJob)
        .options(
            selectinload(GenerationJob.model_mode)
            .selectinload(ModelMode.model)
        )
        .where(GenerationJob.user_id == user_id)
    )
    if status:
        query = query.where(GenerationJob.status == status)

    query = query.order_by(GenerationJob.created_at.desc()).limit(limit).offset(offset)
    result = await self.session.execute(query)
    return list(result.scalars().all())
```

---

## Шаги реализации

1. **Создать схемы** `app/api/schemas/generation.py`
   - Request и Response модели

2. **Обновить GenerationJobRepository**
   - Добавить `get_user_jobs_count()`
   - Добавить `get_user_jobs_filtered()` с eager loading model_mode.model
   - Добавить eager loading в существующие методы

3. **Создать роут** `app/api/routes/generations.py`
   - `POST /api/generations`
   - `GET /api/generations`
   - `GET /api/generations/{job_id}`

4. **Зарегистрировать роут** в `app/api/__init__.py`

5. **Написать тесты** `tests/api/test_generations.py`
   - Создание генерации (успех)
   - Создание с недостаточным балансом
   - Создание с несуществующим mode
   - Список генераций с пагинацией
   - Получение одной генерации
   - 404 для чужой генерации
   - 401 без авторизации

6. **Проверить** — isort, black, flake8, pyright, pytest

---

## Открытые вопросы (AICODE-QUESTION)

1. **Background task:** Как запускать polling KIE API?
   - Вариант A: FastAPI BackgroundTasks (простой)
   - Вариант B: Celery/ARQ (масштабируемый)
   - Вариант C: Отдельный polling service (cron)

2. **Refund при ошибке:** Автоматический или ручной?

3. **Rate limiting:** Нужен ли лимит на генерации в минуту?

---

## Риски и митигация

| Риск | Митигация |
|------|-----------|
| Race condition при списании кредитов | Транзакционность в deps.py (commit в конце) |
| KIE API недоступен | Создаём job со статусом queue, retry в background |
| Долгий polling блокирует | Background task, не блокирует HTTP response |
| N+1 при загрузке mode.model | Eager loading через selectinload |

---

## Definition of Done

- [x] Схемы созданы
- [x] Repository обновлён
- [x] Роуты реализованы
- [x] Роутер зарегистрирован
- [x] Тесты написаны и проходят
- [x] Код проверен (isort, black, flake8, pyright)
- [x] Background task задокументирован как TODO
- [ ] Обновлён roadmap (пункт 2.4)
