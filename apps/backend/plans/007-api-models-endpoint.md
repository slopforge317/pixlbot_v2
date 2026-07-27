# План 007: API эндпоинты — Модели

**Статус:** DONE
**Roadmap:** 2.3 API эндпоинты — Модели
**Зависимости:** AiModelRepository, ModelModeRepository (готовы)

---

## Цель

Реализовать эндпоинты для получения списка AI моделей и их режимов (modes) для TMA.

---

## Эндпоинты

### GET /api/models

**Описание:** Список всех AI моделей с активными режимами

**Auth:** Required (`Authorization: tma <initData>`)

**Query params:**
- `type` (optional): `image` | `video` — фильтр по типу контента

**Response:** `200 OK`
```json
{
  "models": [
    {
      "id": 1,
      "name": "Stable Diffusion XL",
      "description": "High quality image generation",
      "type": "image",
      "modes": [
        {
          "id": 1,
          "name": "Standard",
          "description": "1024x1024, 30 steps",
          "price": 10
        },
        {
          "id": 2,
          "name": "HD",
          "description": "2048x2048, 50 steps",
          "price": 25
        }
      ]
    }
  ]
}
```

**Логика:**
1. Получить `user` через `CurrentUser` dependency
2. Вызвать `AiModelRepository.get_all_with_modes()` или `get_by_type(type)`
3. Отфильтровать только `is_active=True` modes (уже делается в репо)
4. Вернуть список моделей с вложенными modes

---

### GET /api/models/{model_id}

**Описание:** Детали одной модели с её режимами

**Auth:** Required

**Path params:**
- `model_id`: int

**Response:** `200 OK` — одна модель с modes

**Response:** `404 Not Found` — модель не найдена
```json
{
  "detail": "Model not found"
}
```

**Логика:**
1. Вызвать `AiModelRepository.get_with_modes(model_id)`
2. Если `None` → HTTPException 404
3. Вернуть модель с modes

---

## Pydantic Schemas

**Файл:** `app/api/schemas/ai_model.py`

```python
from pydantic import BaseModel


class ModelModeResponse(BaseModel):
    """Режим генерации (response)."""

    id: int
    name: str
    description: str | None
    price: int  # credits

    model_config = {"from_attributes": True}


class AIModelResponse(BaseModel):
    """AI модель с режимами (response)."""

    id: int
    name: str
    description: str | None
    type: str  # "image" | "video"
    modes: list[ModelModeResponse]

    model_config = {"from_attributes": True}


class AIModelListResponse(BaseModel):
    """Список моделей (response)."""

    models: list[AIModelResponse]
```

---

## Route Handler

**Файл:** `app/api/routes/models.py`

```python
"""AI Models API endpoints."""

from fastapi import APIRouter, HTTPException, Query

from api.deps import CurrentUser, DBSession
from api.schemas.ai_model import AIModelListResponse, AIModelResponse
from db.enums import ContentType
from db.repositories.ai_model import AiModelRepository

router = APIRouter(prefix="/api", tags=["models"])


@router.get("/models", response_model=AIModelListResponse)
async def list_models(
    user: CurrentUser,
    session: DBSession,
    type: ContentType | None = Query(None, description="Filter by content type"),
) -> AIModelListResponse:
    """
    Get list of AI models with their active modes.

    Optionally filter by type (image/video).
    """
    repo = AiModelRepository(session)

    if type:
        models = await repo.get_by_type(type)
    else:
        models = await repo.get_all_with_modes()

    return AIModelListResponse(models=models)


@router.get("/models/{model_id}", response_model=AIModelResponse)
async def get_model(
    model_id: int,
    user: CurrentUser,
    session: DBSession,
) -> AIModelResponse:
    """Get single AI model with its active modes."""
    repo = AiModelRepository(session)
    model = await repo.get_with_modes(model_id)

    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    return AIModelResponse.model_validate(model)
```

---

## Шаги реализации

1. **Создать схемы** `app/api/schemas/ai_model.py`
   - `ModelModeResponse`
   - `AIModelResponse`
   - `AIModelListResponse`

2. **Создать роут** `app/api/routes/models.py`
   - `GET /api/models`
   - `GET /api/models/{model_id}`

3. **Зарегистрировать роут** в `app/api/__init__.py`
   ```python
   from api.routes.models import router as models_router
   app.include_router(models_router)
   ```

4. **Написать тесты** `tests/api/test_models.py`
   - Тест списка моделей
   - Тест фильтрации по типу
   - Тест получения одной модели
   - Тест 404 для несуществующей модели
   - Тест 401 без авторизации

5. **Проверить**
   - `PYTHONPATH=app poetry run pytest tests/api/test_models.py -v`
   - Полный цикл: isort → black → flake8 → pyright

---

## Тесты

```python
# tests/api/test_models.py

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_models_unauthorized(client: AsyncClient):
    """Should return 401 without auth."""
    response = await client.get("/api/models")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_models(auth_client: AsyncClient, seed_models):
    """Should return list of models with modes."""
    response = await auth_client.get("/api/models")
    assert response.status_code == 200
    data = response.json()
    assert "models" in data
    assert len(data["models"]) > 0
    assert "modes" in data["models"][0]


@pytest.mark.asyncio
async def test_list_models_filter_by_type(auth_client: AsyncClient, seed_models):
    """Should filter models by content type."""
    response = await auth_client.get("/api/models?type=image")
    assert response.status_code == 200
    data = response.json()
    for model in data["models"]:
        assert model["type"] == "image"


@pytest.mark.asyncio
async def test_get_model(auth_client: AsyncClient, seed_models):
    """Should return single model with modes."""
    response = await auth_client.get("/api/models/1")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert "modes" in data


@pytest.mark.asyncio
async def test_get_model_not_found(auth_client: AsyncClient):
    """Should return 404 for non-existent model."""
    response = await auth_client.get("/api/models/999")
    assert response.status_code == 404
```

---

## Риски и митигация

| Риск | Митигация |
|------|-----------|
| N+1 queries при загрузке modes | Используем `selectinload` в `get_all_with_modes()` (уже реализовано) |
| Неактивные modes попадают в ответ | Фильтрация в репозитории (уже реализовано) |
| Пустой список modes у модели | Допустимо — TMA покажет "нет доступных режимов" |

---

## Definition of Done

- [ ] Схемы созданы и типизированы
- [ ] Роуты реализованы
- [ ] Роутер зарегистрирован
- [ ] Тесты написаны и проходят
- [ ] isort, black, flake8, pyright — без ошибок
- [ ] Обновлён roadmap (пункт 2.3 отмечен как выполненный)
