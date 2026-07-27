# План 009: API эндпоинты — Пакеты кредитов

**Статус:** DONE
**Roadmap:** 2.5 API эндпоинты — Пакеты кредитов
**Зависимости:** CreditPackageRepository (готов)

---

## Цель

Реализовать эндпоинт для получения списка активных пакетов кредитов для покупки в TMA.

---

## Эндпоинты

### GET /api/packages

**Описание:** Список активных пакетов кредитов, отсортированных по цене

**Auth:** Required (`Authorization: tma <initData>`)

**Query params:** нет

**Response:** `200 OK`
```json
{
  "packages": [
    {
      "id": 1,
      "name": "Starter",
      "description": "Perfect for trying out",
      "credit_amount": 50,
      "price": 9900,
      "price_formatted": "99.00 ₽"
    },
    {
      "id": 2,
      "name": "Standard",
      "description": "Most popular choice",
      "credit_amount": 150,
      "price": 24900,
      "price_formatted": "249.00 ₽"
    },
    {
      "id": 3,
      "name": "Pro",
      "description": "Best value",
      "credit_amount": 500,
      "price": 69900,
      "price_formatted": "699.00 ₽"
    }
  ]
}
```

**Логика:**
1. Получить `user` через `CurrentUser` dependency
2. Вызвать `CreditPackageRepository.get_active_ordered_by_price()`
3. Форматировать цены для отображения
4. Вернуть список пакетов

---

## Pydantic Schemas

**Файл:** `app/api/schemas/credit_package.py`

```python
from pydantic import BaseModel, computed_field


class CreditPackageResponse(BaseModel):
    """Пакет кредитов (response)."""

    id: int
    name: str
    description: str | None
    credit_amount: int
    price: int  # в копейках

    model_config = {"from_attributes": True}

    @computed_field
    @property
    def price_formatted(self) -> str:
        """Цена в формате '99.00 ₽'."""
        rubles = self.price / 100
        return f"{rubles:.2f} ₽"


class CreditPackageListResponse(BaseModel):
    """Список пакетов (response)."""

    packages: list[CreditPackageResponse]
```

---

## Route Handler

**Файл:** `app/api/routes/packages.py`

```python
"""Credit Packages API endpoints."""

from fastapi import APIRouter

from api.deps import CurrentUser, DBSession
from api.schemas.credit_package import CreditPackageListResponse
from db.repositories.credit_package import CreditPackageRepository

router = APIRouter(prefix="/api", tags=["packages"])


@router.get("/packages", response_model=CreditPackageListResponse)
async def list_packages(
    user: CurrentUser,
    session: DBSession,
) -> CreditPackageListResponse:
    """
    Get list of available credit packages for purchase.

    Packages are sorted by price (ascending).
    """
    repo = CreditPackageRepository(session)
    packages = await repo.get_active_ordered_by_price()

    return CreditPackageListResponse(packages=packages)
```

---

## Шаги реализации

1. **Создать схемы** `app/api/schemas/credit_package.py`
   - `CreditPackageResponse` с computed_field для форматирования цены
   - `CreditPackageListResponse`

2. **Создать роут** `app/api/routes/packages.py`
   - `GET /api/packages`

3. **Зарегистрировать роут** в `app/api/__init__.py`
   ```python
   from api.routes.packages import router as packages_router
   app.include_router(packages_router)
   ```

4. **Написать тесты** `tests/api/test_packages.py`
   - Тест получения списка пакетов
   - Тест сортировки по цене
   - Тест форматирования цены
   - Тест 401 без авторизации
   - Тест пустого списка (нет активных пакетов)

5. **Проверить** — isort, black, flake8, pyright, pytest

---

## Тесты

```python
# tests/api/test_packages.py

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_packages_unauthorized(client: AsyncClient):
    """Should return 401 without auth."""
    response = await client.get("/api/packages")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_packages(auth_client: AsyncClient, seed_packages):
    """Should return list of active packages."""
    response = await auth_client.get("/api/packages")
    assert response.status_code == 200
    data = response.json()
    assert "packages" in data
    assert len(data["packages"]) > 0


@pytest.mark.asyncio
async def test_packages_sorted_by_price(auth_client: AsyncClient, seed_packages):
    """Packages should be sorted by price ascending."""
    response = await auth_client.get("/api/packages")
    data = response.json()
    prices = [p["price"] for p in data["packages"]]
    assert prices == sorted(prices)


@pytest.mark.asyncio
async def test_package_price_formatted(auth_client: AsyncClient, seed_packages):
    """Package should have formatted price."""
    response = await auth_client.get("/api/packages")
    data = response.json()
    package = data["packages"][0]
    assert "price_formatted" in package
    assert "₽" in package["price_formatted"]


@pytest.mark.asyncio
async def test_list_packages_empty(auth_client: AsyncClient):
    """Should return empty list if no active packages."""
    # No seed_packages fixture = no packages in DB
    response = await auth_client.get("/api/packages")
    assert response.status_code == 200
    data = response.json()
    assert data["packages"] == []
```

---

## Риски и митигация

| Риск | Митигация |
|------|-----------|
| Неактивные пакеты попадают в ответ | Фильтрация `is_active=True` в репозитории |
| Неправильное форматирование цены | Тест на формат + computed_field в Pydantic |
| Пустой список пакетов | Допустимо — TMA покажет "нет доступных пакетов" |

---

## Возможные расширения (не в текущем скоупе)

- `GET /api/packages/{id}` — детали одного пакета
- Локализация цен (USD, EUR)
- Промокоды и скидки
- Лимиты на покупку (max пакетов в день)

---

## Definition of Done

- [x] Схемы созданы
- [x] Роут реализован
- [x] Роутер зарегистрирован
- [x] Тесты написаны и проходят
- [x] Код проверен (isort, black, flake8, pyright)
- [x] Обновлён roadmap (пункт 2.5 отмечен как выполненный)
