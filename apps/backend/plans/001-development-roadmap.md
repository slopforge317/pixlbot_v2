# План разработки pixlbot

**Статус:** DRAFT
**Цель:** Backend (FastAPI + Bot) для TMA-приложения генерации изображений и видео через kei.ai API

---

## Архитектура

- **TMA (Telegram Mini App)** — весь UI/UX (выбор модели, промпт, история, баланс, покупки)
- **FastAPI Backend** — API для TMA, оркестрация генерации, платежи
- **Telegram Bot** — только уведомления и отправка готовых медиа

---

## Фаза 1: Фундамент

### 1.1 База данных
- [x] SQLAlchemy модели по схеме из `docs/structure.md`
- [ ] Миграции (alembic) — отложено
- [x] Базовые CRUD операции (repositories)

### 1.2 Сервис KIE API
- [x] HTTP клиент для API генерации
- [x] Модели запросов/ответов (Pydantic schemas)
- [x] Обработка статусов задач (polling)
- [ ] Callback (webhook) — отложено

### 1.3 Сервис кредитов
- [ ] Логика баланса пользователя
- [ ] Списание за генерацию
- [ ] Пополнение при покупке
- [ ] Возврат при ошибке

### 1.4 Недостающие Repositories
- [x] `AiModelRepository` — CRUD для моделей
- [x] `ModelModeRepository` — CRUD для режимов + фильтр по is_active
- [x] `CreditPackageRepository` — CRUD для пакетов + фильтр по is_active
- [x] `TransactionRepository` — история транзакций пользователя

---

## Фаза 2: FastAPI Backend (для TMA)

### 2.1 Аутентификация
- [x] Валидация Telegram InitData
- [x] Middleware авторизации
- [x] Получение/создание пользователя

### 2.2 API эндпоинты — Пользователь
- [x] `GET /api/me` — профиль и баланс
  - Модели: `users`, `transactions`
  - Repository: `UserRepository.get_balance()`
- [ ] `GET /api/transactions` — история транзакций
  - Модели: `transactions`
  - Repository: `TransactionRepository`

### 2.3 API эндпоинты — Модели
- [x] `GET /api/models` — список AI моделей с режимами
  - Модели: `ai_models`, `model_modes`
  - Repository: `AiModelRepository`, `ModelModeRepository`
- [x] `GET /api/models/{id}` — детали модели

### 2.4 API эндпоинты — Генерация
- [x] `POST /api/generations` — создание генерации
  - Модели: `generations_job`, `model_modes`, `transactions`
  - Логика: проверка баланса → списание → создание job → отправка в KIE
- [x] `GET /api/generations` — история генераций (с пагинацией)
  - Модели: `generations_job`
  - Repository: `GenerationJobRepository.get_user_jobs()`
- [x] `GET /api/generations/{id}` — статус/детали генерации
  - Модели: `generations_job`

### 2.5 API эндпоинты — Пакеты кредитов
- [x] `GET /api/packages` — список активных пакетов
  - Модели: `credit_packages`
  - Repository: `CreditPackageRepository`

### 2.6 Генерация — бизнес-логика
- [x] Приём запроса от TMA
- [x] Проверка баланса
- [x] Списание кредитов (создание transaction)
- [x] Отправка в kei.ai
- [x] Background polling статуса
- [x] Триггер уведомления в бот при завершении
- [x] Возврат кредитов при ошибке

---

## Фаза 3: Telegram Bot (уведомления)

### 3.1 Базовые команды
- [x] /start — приветствие + кнопка открытия TMA
- [x] /help — справка (направление в TMA)
- [x] /balance — баланс (направление в TMA)

### 3.2 Уведомления
- [x] Отправка готовых изображений
- [x] Отправка готовых видео
- [x] Уведомление об ошибке генерации
- [x] Уведомление о платеже (подготовлено)

### 3.3 Webhook
- [x] Переход с polling на webhook
- [x] Интеграция с FastAPI

---

## Фаза 4: Платежи

### 4.1 Repositories
- [ ] `PaymentRepository` — CRUD для платежей

### 4.2 API эндпоинты
- [ ] `POST /api/payments` — инициация платежа
  - Модели: `payments`, `credit_packages`
- [ ] `POST /api/payments/webhook` — callback от провайдера
  - Модели: `payments`, `transactions`
- [ ] `GET /api/payments/{id}` — статус платежа (опционально)

### 4.3 Интеграция
- [ ] Выбор провайдера (Telegram Payments / ЮKassa / другой)
- [ ] Формирование платёжной ссылки
- [ ] Обработка webhook результата
- [ ] Начисление кредитов при успехе

---

## Фаза 5: Расширение

### 5.1 Генерация видео
- [ ] Добавление видео-моделей (Kling, Veo, Sora)
- [ ] Обработка длительных задач

### 5.2 Reference images (img2img)
- [ ] `POST /api/uploads` — загрузка reference изображений
- [ ] Временное хранилище или S3
- [ ] Возможно новая модель `uploads`

### 5.3 WebSocket для realtime
- [ ] `WS /api/ws/generations/{id}` — статус генерации в реальном времени
- [ ] Альтернатива: Server-Sent Events (SSE)

### 5.4 TMA Frontend
- [ ] Разработка UI (отдельный репозиторий)
- [ ] Интеграция с backend API

---

## Открытые вопросы

1. **API kei.ai** — нужна документация (эндпоинты, формат, лимиты)
2. **Платёжный провайдер** — какой использовать?
3. **Начальный баланс** — сколько бесплатных кредитов новым пользователям?
4. **Цены генераций** — стоимость в кредитах для каждой модели?
5. **Обработка ошибок** — политика возврата кредитов?
6. **Reference images** — нужна ли поддержка img2img в MVP?

---

## Порядок реализации (рекомендуемый)

```
Фаза 1: Repositories → Credit service
    ↓
Фаза 2: FastAPI auth → API endpoints → Generation flow
    ↓
Фаза 3: Bot notifications
    ↓
Фаза 4: Payments (после MVP)
    ↓
Фаза 5: Video, uploads, WebSocket
```

**Важно:** TMA frontend разрабатывается параллельно в отдельном проекте.
