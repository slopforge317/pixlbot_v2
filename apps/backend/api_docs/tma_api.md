# TMA Backend API

Документация для подключения Telegram Mini App frontend к `tma-backend`.

Backend также отдает автоматическую OpenAPI-документацию:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

## Base URL

Локально:

```text
http://localhost:8000
```

Для frontend удобно хранить API prefix в переменной:

```env
VITE_API_URL=http://localhost:8000/api
```

Тогда запросы из frontend идут на `VITE_API_URL + endpoint`, например:

```text
GET http://localhost:8000/api/me
```

## Authentication

Все TMA endpoints под `/api` требуют Telegram Mini App initData:

```http
Authorization: tma <initData>
```

`initData` берется из Telegram WebApp:

```ts
window.Telegram.WebApp.initData
```

Для локальной разработки без Telegram можно сгенерировать валидный mock initData:

```powershell
cd C:\Users\dev\projects\bot\tma-backend
$env:PYTHONPATH="app"
poetry run python scripts/generate_init_data.py
```

Скрипт использует `BOT_TOKEN` из `.env`, поэтому token в backend env должен совпадать с token, которым backend валидирует initData.

Пример frontend env:

```env
VITE_API_URL=http://localhost:8000/api
VITE_MOCK_INIT_DATA=<output from scripts/generate_init_data.py>
```

Если header отсутствует или initData невалидный, backend вернет `401`.

## Common Headers

Для JSON-запросов:

```http
Authorization: tma <initData>
Content-Type: application/json
```

Для `GET` запросов `Content-Type` не нужен.

## Common Error Shape

FastAPI обычно возвращает ошибки так:

```json
{
  "detail": "Error message"
}
```

Для ошибки недостаточного баланса форма другая:

```json
{
  "detail": {
    "detail": "Insufficient credits",
    "balance": 5,
    "required": 10
  }
}
```

## Enums

### JobStatus

Статусы генерации:

| Value | Meaning | Frontend behavior |
| --- | --- | --- |
| `queue` | Задача создана и ждет обработки | Показывать "в очереди" |
| `processing` | Задача выполняется у provider/KIE | Показывать "в обработке" |
| `done` | Генерация завершилась успешно | Показывать результат, разрешить send-original |
| `error` | Генерация завершилась ошибкой | Показывать ошибку, кредиты возвращаются backend'ом |

### PaymentStatus

Статусы платежа:

| Value | Meaning |
| --- | --- |
| `pending` | Платеж создан, оплата еще не подтверждена |
| `success` | Платеж успешен, кредиты должны быть начислены |
| `failed` | Платеж неуспешен |

### ContentType

Типы генерации:

| Value | Meaning |
| --- | --- |
| `image` | Image generation |
| `video` | Video generation |

### ModelStatus

Тир модели. Возвращается как `model.status`, может быть `null`.

| Value |
| --- |
| `Pro` |
| `Basic` |
| `Basic*` |

## Endpoints

## GET /health

Health check. Не требует TMA auth.

### Response 200

```json
{
  "status": "ok"
}
```

## GET /api/me

Возвращает текущего пользователя и баланс. Если пользователя еще нет в базе, backend создает его из Telegram initData.

### Request

```http
GET /api/me
Authorization: tma <initData>
```

### Response 200

```json
{
  "user_id": 1,
  "telegram_user_id": 123456789,
  "first_name": "Dev",
  "last_name": "User",
  "username": "devuser",
  "balance": 100,
  "created_at": "2026-07-09T10:00:00.000000"
}
```

### Errors

| Status | Reason |
| --- | --- |
| `401` | Missing/invalid `Authorization`, invalid initData signature, expired initData |

## GET /api/providers

Возвращает active providers, models и pricing variants. Это главный endpoint для построения формы генерации.

### Query Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `gen_type` | `image` или `video` | no | Фильтр по типу генерации |

### Request

```http
GET /api/providers?gen_type=image
Authorization: tma <initData>
```

### Response 200

```json
{
  "providers": [
    {
      "id": 1,
      "title": "Seedream",
      "gen_type": "image",
      "models": [
        {
          "id": 10,
          "api_model_id": "seedream/4.5-text-to-image",
          "title": "Seedream 4.5 Text to Image",
          "input_schema": {
            "prompt": {
              "type": "string",
              "required": true,
              "ui_label": "Prompt",
              "ui_order": 1,
              "max_length": 2000
            },
            "aspect_ratio": {
              "type": "string",
              "required": true,
              "ui_label": "Aspect ratio",
              "ui_order": 2,
              "default": "1:1",
              "values": ["1:1", "4:5", "9:16", "16:9"],
              "variant": true
            }
          },
          "variant_keys": ["aspect_ratio"],
          "pricing": [
            {
              "id": 100,
              "variant_values": {
                "aspect_ratio": "1:1"
              },
              "price": 10
            }
          ],
          "status": "Pro"
        }
      ]
    }
  ]
}
```

### Frontend notes

`input_schema` управляет формой:

| Field property | Meaning |
| --- | --- |
| `type` | `string`, `boolean` или `array` |
| `required` | Поле обязательно |
| `ui_label` | Label для UI |
| `ui_order` | Порядок отображения |
| `default` | Значение по умолчанию |
| `values` | Допустимые значения для select/carousel |
| `max_length` | Максимальная длина строки. Иногда может быть `true`, frontend должен это игнорировать как число |
| `variant` | Поле влияет на выбор pricing variant |
| `max_images` | Максимум изображений для image upload поля |
| `max_image_size_mb` | Максимальный размер одного изображения |

`variant_keys` показывает, какие поля участвуют в выборе цены. Чтобы выбрать `pricing`:

1. Взять текущие значения формы для всех `variant_keys`.
2. Найти pricing variant, у которого `variant_values` совпадает с этими значениями.
3. Передать выбранный variant в `POST /api/generations`.

### Errors

| Status | Reason |
| --- | --- |
| `401` | Auth error |

## POST /api/generations

Создает задачу генерации, списывает кредиты и запускает background processing.

### Request

```http
POST /api/generations
Authorization: tma <initData>
Content-Type: application/json
```

```json
{
  "model": {
    "id": 10,
    "api_model_id": "seedream/4.5-text-to-image",
    "title": "Seedream 4.5 Text to Image"
  },
  "variant": {
    "id": 100,
    "price": 10,
    "variant_values": {
      "aspect_ratio": "1:1"
    }
  },
  "input": {
    "prompt": "A clean studio product photo",
    "aspect_ratio": "1:1"
  }
}
```

### Request Fields

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `model.id` | number | yes | Model id from `/api/providers` |
| `model.api_model_id` | string | yes | Provider model id from `/api/providers` |
| `model.title` | string | yes | Human-readable title |
| `variant.id` | number | yes | Pricing variant id from selected model |
| `variant.price` | number | yes | Price from selected pricing variant |
| `variant.variant_values` | object | yes | Variant values from selected pricing variant |
| `input.prompt` | string | yes | Prompt. Must be non-empty, max 2000 chars |
| `input.*` | any | depends on model | Values from model `input_schema` |

For image-to-image models, frontend first uploads files through `/api/storage/presign-upload`, then sends object keys in the relevant image array field:

```json
{
  "input": {
    "prompt": "Make it cinematic",
    "image_urls": [
      "uploads/1/550e8400-e29b-41d4-a716-446655440000.png"
    ]
  }
}
```

Backend replaces valid object keys with temporary download URLs before calling KIE.

### Response 201

```json
{
  "job_id": 123,
  "status": "queue",
  "pricing_variant_id": 100,
  "cost_credit": 10,
  "prompt": "A clean studio product photo",
  "created_at": "2026-07-09T10:00:00.000000"
}
```

### Side effects

- Backend validates pricing variant exists and is active.
- Backend checks that client price equals current DB price.
- Backend checks user balance.
- Backend creates generation job.
- Backend deducts credits immediately.
- Backend starts background generation.
- If generation later fails or times out, backend sets status `error` and refunds credits.

### Errors

| Status | Reason | Body |
| --- | --- | --- |
| `400` | Missing/invalid prompt | FastAPI validation error |
| `400` | Insufficient credits | `{"detail":{"detail":"Insufficient credits","balance":5,"required":10}}` |
| `401` | Auth error | `{"detail":"..."}` |
| `404` | Pricing variant not found or inactive | `{"detail":"Pricing variant not found or inactive"}` |
| `409` | Price changed since frontend loaded providers | `{"detail":"Price has changed. Please refresh and try again."}` |

## GET /api/generations

Возвращает историю генераций текущего пользователя.

### Query Parameters

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `limit` | number | no | `10` | Min `1`, max `50` |
| `offset` | number | no | `0` | Min `0` |
| `status` | `queue`, `processing`, `done`, `error` | no | none | Фильтр по статусу |

### Request

```http
GET /api/generations?limit=10&offset=0
Authorization: tma <initData>
```

### Response 200

```json
{
  "generations": [
    {
      "job_id": 123,
      "status": "done",
      "pricing_variant_id": 100,
      "cost_credit": 10,
      "prompt": "A clean studio product photo",
      "created_at": "2026-07-09T10:00:00.000000",
      "model_title": "Seedream 4.5 Text to Image",
      "provider_title": "Seedream",
      "params": {
        "prompt": "A clean studio product photo",
        "aspect_ratio": "1:1"
      },
      "result_url": "https://example.com/result.png",
      "error_message": null,
      "completed_at": "2026-07-09T10:01:00.000000"
    }
  ],
  "total": 1,
  "limit": 10,
  "offset": 0
}
```

### Field notes

| Field | Meaning |
| --- | --- |
| `result_url` | URL результата. Обычно есть только при `status = done` |
| `error_message` | Текст ошибки. Обычно есть только при `status = error` |
| `params` | Input, с которым была создана генерация |
| `total` | Общее количество jobs текущего пользователя с учетом `status` фильтра |

### Errors

| Status | Reason |
| --- | --- |
| `401` | Auth error |
| `422` | Invalid query params |

## GET /api/generations/{job_id}

Возвращает одну генерацию текущего пользователя.

### Request

```http
GET /api/generations/123
Authorization: tma <initData>
```

### Response 200

```json
{
  "job_id": 123,
  "status": "done",
  "pricing_variant_id": 100,
  "cost_credit": 10,
  "prompt": "A clean studio product photo",
  "created_at": "2026-07-09T10:00:00.000000",
  "model_title": "Seedream 4.5 Text to Image",
  "provider_title": "Seedream",
  "params": {
    "prompt": "A clean studio product photo",
    "aspect_ratio": "1:1"
  },
  "result_url": "https://example.com/result.png",
  "error_message": null,
  "completed_at": "2026-07-09T10:01:00.000000"
}
```

### Errors

| Status | Reason |
| --- | --- |
| `401` | Auth error |
| `404` | Generation not found or belongs to another user |

## POST /api/generations/{job_id}/send-original

Отправляет результат генерации пользователю в Telegram как document в оригинальном качестве.

### Request

```http
POST /api/generations/123/send-original
Authorization: tma <initData>
```

Body не нужен.

### Response 200

```json
{
  "success": true,
  "message": "Document sent"
}
```

### Requirements

- Job должен принадлежать текущему пользователю.
- Job должен иметь `status = done`.
- Job должен иметь `result_url`.

### Errors

| Status | Reason |
| --- | --- |
| `400` | Generation is not completed |
| `400` | No result file available |
| `401` | Auth error |
| `404` | Generation not found or belongs to another user |
| `502` | Failed to send document to Telegram |

## GET /api/packages

Возвращает active credit packages для покупки. Сортировка по цене по возрастанию.

### Request

```http
GET /api/packages
Authorization: tma <initData>
```

### Response 200

```json
{
  "packages": [
    {
      "id": 1,
      "name": "Start",
      "description": "20 Pro generations",
      "credit_amount": 200,
      "price": 59000,
      "price_formatted": "590.00 ₽"
    }
  ]
}
```

### Field notes

| Field | Meaning |
| --- | --- |
| `credit_amount` | Сколько credits будет начислено |
| `price` | Цена в копейках |
| `price_formatted` | Форматированная цена |

### Errors

| Status | Reason |
| --- | --- |
| `401` | Auth error |

## POST /api/payments

Создает платеж YooKassa для выбранного credit package.

### Request

```http
POST /api/payments
Authorization: tma <initData>
Content-Type: application/json
```

```json
{
  "credit_package_id": 1,
  "email": "user@example.com"
}
```

### Response 200

```json
{
  "payment_id": 42,
  "confirmation_url": "https://yoomoney.ru/checkout/payments/v2/contract?orderId=..."
}
```

### Frontend behavior

Открыть `confirmation_url`:

- в Telegram Mini App: `window.Telegram.WebApp.openLink(confirmation_url)` или `openInvoice`, если checkout URL подходит под Telegram flow;
- в обычном браузере: `window.open(confirmation_url, "_blank")`.

После возврата из YooKassa можно проверять статус через `GET /api/payments/{payment_id}/status`.

### Errors

| Status | Reason |
| --- | --- |
| `401` | Auth error |
| `404` | Credit package not found |
| `422` | Invalid email or request body |
| `502` | Payment service unavailable |
| `503` | Payments are not configured |

## GET /api/payments/{payment_id}/status

Проверяет статус платежа текущего пользователя.

### Request

```http
GET /api/payments/42/status
Authorization: tma <initData>
```

### Response 200

```json
{
  "payment_id": 42,
  "status": "pending"
}
```

`status` одно из:

- `pending`
- `success`
- `failed`

### Errors

| Status | Reason |
| --- | --- |
| `401` | Auth error |
| `404` | Payment not found or belongs to another user |

## POST /api/storage/presign-upload

Создает presigned PUT URL для прямой загрузки изображения в S3-compatible storage.

### Request

```http
POST /api/storage/presign-upload
Authorization: tma <initData>
Content-Type: application/json
```

```json
{
  "content_type": "image/png",
  "file_size": 123456
}
```

### Allowed content types

| MIME type | Extension |
| --- | --- |
| `image/jpeg` | `jpg` |
| `image/png` | `png` |
| `image/webp` | `webp` |

Default max file size is controlled by backend env:

```env
S3_UPLOAD_MAX_SIZE_BYTES=10485760
```

### Response 200

```json
{
  "upload_url": "https://storage.yandexcloud.net/bucket/uploads/1/file.png?...",
  "object_key": "uploads/1/550e8400-e29b-41d4-a716-446655440000.png",
  "content_type": "image/png"
}
```

### Upload flow

1. Frontend calls `/api/storage/presign-upload`.
2. Frontend uploads file directly:

```ts
await fetch(upload_url, {
  method: "PUT",
  headers: {
    "Content-Type": content_type,
  },
  body: file,
})
```

3. Frontend sends returned `object_key` in `POST /api/generations` input field for images.

### Errors

| Status | Reason |
| --- | --- |
| `400` | Unsupported content type, non-positive file size, file too large |
| `401` | Auth error |
| `422` | Invalid request body |
| `503` | Storage service is not configured |

## Webhook Endpoints

Эти endpoints не нужны TMA frontend напрямую.

| Method | Path | Used by |
| --- | --- | --- |
| `POST` | `/webhook/telegram` | Telegram webhook mode |
| `POST` | `/webhook/kie/{secret}` | KIE callback mode |
| `POST` | `/webhook/yookassa` | YooKassa payment notifications |

## Minimal Frontend Data Flow

### App bootstrap

1. Get `initData` from Telegram or `VITE_MOCK_INIT_DATA`.
2. Call `GET /api/me`.
3. Call `GET /api/providers`.
4. Call `GET /api/packages` when payment screen opens.
5. Call `GET /api/generations` when history screen opens.

### Generation flow

1. User selects provider/model.
2. UI builds form from selected `model.input_schema`.
3. UI calculates selected pricing variant from `model.variant_keys` and `model.pricing`.
4. If image files are attached, upload each through `/api/storage/presign-upload`.
5. Call `POST /api/generations`.
6. Show created job with status `queue`.
7. Refresh history periodically or on screen open.

### Payment flow

1. Load packages with `GET /api/packages`.
2. User chooses package and enters email.
3. Call `POST /api/payments`.
4. Open `confirmation_url`.
5. Check `GET /api/payments/{payment_id}/status` after return or by polling.

