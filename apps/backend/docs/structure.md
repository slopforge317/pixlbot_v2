# Architecture and Code Structure

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Telegram Mini App (TMA)                      │
│         All UI/UX: model selection, prompts, history,           │
│              balance, payments, settings                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼ HTTP/WebSocket
┌─────────────────────────────────────────────────────────────────┐
│                     FastAPI Backend                             │
│   - REST API for TMA                                            │
│   - Telegram InitData auth                                      │
│   - Generation orchestration                                    │
│   - Payment processing                                          │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
┌─────────────────────────┐     ┌─────────────────────────┐
│    Telegram Bot         │     │      KIE.ai API         │
│  (notifications only)   │     │   (AI generation)       │
│  - Send ready media     │     │                         │
│  - Status updates       │     │                         │
│  - /start → open TMA    │     │                         │
└─────────────────────────┘     └─────────────────────────┘
```

## Directory Structure

```
app/
├── api/                    # FastAPI endpoints (primary interface for TMA)
│   ├── __init__.py        # App factory (create_app)
│   ├── deps.py            # Dependencies (get_db_session, get_current_user)
│   ├── routes/            # API route handlers
│   │   ├── users.py       # GET /api/me
│   │   ├── models.py      # GET /api/providers
│   │   ├── packages.py    # GET /api/packages
│   │   └── generations.py # POST/GET /api/generations, GET /api/generations/{id}
│   └── schemas/           # Pydantic request/response models
│       ├── auth.py        # TelegramUser, TelegramInitData
│       ├── user.py        # UserResponse, UserBalanceResponse
│       ├── ai_model.py    # ProviderResponse, AIModelResponse, PricingVariantResponse
│       ├── credit_package.py # CreditPackageResponse
│       └── generation.py  # GenerationCreateRequest, GenerationResponse
├── bot/                    # Telegram bot (notifications only)
│   └── handlers.py        # /start, notification sending
├── services/
│   ├── auth/              # Telegram InitData authentication
│   │   ├── init_data.py   # validate_init_data() with HMAC-SHA256
│   │   └── exceptions.py  # AuthError, InvalidInitDataError, etc.
│   ├── kie/               # KIE API client for AI generation
│   │   ├── client.py      # Low-level HTTP client
│   │   ├── service.py     # High-level service with polling
│   │   ├── schemas.py     # Pydantic request/response models
│   │   ├── enums.py       # KieTaskState enum
│   │   └── exceptions.py  # Custom exceptions
│   ├── generation.py      # Generation orchestration service
│   └── notification.py    # Bot notification service
├── db/
│   ├── base.py            # SQLAlchemy Base, TimestampMixin
│   ├── session.py         # Engine, session maker, create_tables()
│   ├── enums.py           # PaymentStatus, TransactionType, etc.
│   ├── models/            # SQLAlchemy ORM models
│   │   ├── user.py
│   │   ├── payment.py
│   │   ├── credit_package.py
│   │   ├── transaction.py
│   │   ├── provider.py
│   │   ├── ai_model.py
│   │   ├── pricing_variant.py
│   │   └── generation_job.py
│   └── repositories/      # Data access layer
│       ├── base.py        # Generic CRUD repository
│       ├── user.py        # UserRepository
│       ├── provider.py    # ProviderRepository
│       ├── ai_model.py    # AiModelRepository
│       ├── pricing_variant.py # PricingVariantRepository
│       └── generation.py  # GenerationJobRepository
├── core/
│   ├── config.py          # Pydantic Settings
│   └── logging.py         # Loguru setup
└── main.py                # Entry point (FastAPI + Bot)
```

## Architectural Pattern

**Ports and Adapters (Hexagonal Architecture)** — designed for easy swapping of:
- Database: SQLite → PostgreSQL
- AI Provider: kie.ai → other providers

## Component Responsibilities

### FastAPI Backend (Primary)
- Authenticates TMA requests via Telegram InitData
- Provides REST API for all TMA operations
- Orchestrates generation workflow
- Triggers bot notifications

### Telegram Bot (Secondary)
- Responds to `/start` with Mini App button
- Sends generated images/videos to user chat
- Sends status notifications (success, error, payment)
- No interactive UI — all UI in TMA

**Operating modes:**
- **Webhook** (`WEBHOOK_ENABLED=true`): Integrated with FastAPI, single process (production)
- **Polling** (`WEBHOOK_ENABLED=false`): Separate process, `python -m main` (development)

## Database Architecture

### Design Principles
- **Monetary values:** All financial values stored as integers (no floats)
- **Immutable ledger:** Transactions table is INSERT-only (no UPDATE for history)
- **Flexibility:** Model configs stored as JSON for provider-agnostic schema

### Tables

#### `users`
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| **user_id** | Integer | PK | Internal user ID |
| **telegram_user_id** | BigInteger | Unique | Telegram user ID |
| `first_name` | String(255) | Yes | First name from Telegram |
| `last_name` | String(255) | Nullable | Last name from Telegram |
| `username` | String(255) | Nullable | Username from Telegram |
| `chat_id` | BigInteger | Yes | Chat ID for messaging |
| `utm_source` | String(100) | Yes | Traffic source (default: "direct") |
| `created_at` | Timestamp | Yes | Registration time |

#### `payments`
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| **payment_id** | Integer | PK | Payment ID |
| **user_id** | Integer | FK | Reference to users |
| `status` | Enum | Yes | pending/success/failed |
| `amount_currency` | Integer | Yes | Amount in kopecks/cents |
| `details` | JSON | Yes | Provider metadata |
| `created_at` | Timestamp | Yes | Creation time |

#### `credit_packages`
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| **id** | Integer | PK | Package ID |
| `name` | String(100) | Yes | Package name |
| `description` | Text | Yes | Marketing description |
| `credit_amount` | Integer | Yes | Credits granted |
| `fiat_price` | Integer | Yes | Price in kopecks |
| `is_active` | Boolean | Yes | Available for purchase |

#### `transactions` (Immutable Ledger)
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| **tx_id** | Integer | PK | Transaction ID |
| **user_id** | Integer | FK | Reference to users |
| `type` | Enum | Yes | deposit/withdrawal/refund |
| `amount_credits` | Integer | Yes | Credit amount (+/-) |
| `created_at` | Timestamp | Yes | Transaction time |
| `job_id` | Integer | FK, Nullable | Reference to generations_job |
| `payment_id` | Integer | FK, Nullable | Reference to payments |
| `credit_package_id` | Integer | FK, Nullable | Reference to credit_packages |

#### `providers`
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| **id** | Integer | PK | Provider ID |
| `title` | String(200) | Unique | Provider display name (e.g., "Sora 2 Pro") |
| `gen_type` | String(20) | Yes | Generation type: "image" or "video" |
| `active` | Boolean | Yes | Whether provider is shown to users (default: true) |

#### `ai_models`
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| **id** | Integer | PK | Model ID |
| **provider_id** | Integer | FK | Reference to providers |
| `api_model_id` | String(255) | Unique | Model ID sent to KIE API (e.g., "sora-2-pro-text-to-video") |
| `title` | String(200) | Yes | Display name (e.g., "Text to Video") |
| `input_schema` | JSON | Yes | Parameter schema for frontend UI |
| `variant_keys` | JSON | Yes | Keys used for pricing variants (default: []) |
| `active` | Boolean | Yes | Whether model is available (default: true) |

#### `pricing_variants`
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| **id** | Integer | PK | Variant ID |
| **model_id** | Integer | FK | Reference to ai_models |
| `variant_values` | JSON | Yes | Parameter values for this variant (default: {}) |
| `price` | Integer | Yes | Price in credits (> 0) |
| `active` | Boolean | Yes | Available for use (default: true) |

##### Variant System
Parameters with `variant: true` in `api_parameters.yaml` become `variant_keys` on the model. Each combination of variant values gets its own `pricing_variants` row with a specific price:

| Model | variant_keys | Example pricing rows |
|-------|-------------|---------------------|
| nano-banana-pro | ["resolution"] | {resolution: "2K"}, {resolution: "4K"} |
| seedream/4.5-text-to-image | [] | {} (single price) |
| gpt-image/1.5-* | ["quality"] | {quality: "medium"}, {quality: "high"} |
| sora-2-pro-* | ["n_frames", "size"] | 4 combos (10/15 × standard/high) |
| kling-2.6/* | ["sound", "duration"] | 4 combos (true/false × 5/10) |

##### `input_schema` JSON Structure
The `input_schema` field stores the full parameter definition from `api_parameters.yaml`:
```json
{
  "prompt": {"type": "string", "required": true},
  "aspect_ratio": {"type": "enum", "values": ["1:1", "16:9", "9:16"]},
  "n_frames": {"type": "enum", "values": ["10", "15"], "variant": true},
  "size": {"type": "enum", "values": ["standard", "high"], "variant": true}
}
```
- Parameters with `variant: true` are used for pricing differentiation
- All parameters are sent to the frontend for UI rendering

##### Provider → Model → Pricing Hierarchy
The API presents data as a tree:
```
Provider (providers)
└── Model (ai_models)
    └── PricingVariant (pricing_variants)
```
The `/api/providers` endpoint returns this hierarchy pre-grouped.

#### `generations_job`
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| **job_id** | Integer | PK | Job ID |
| **user_id** | Integer | FK | Reference to users |
| **pricing_variant_id** | Integer | FK | Reference to pricing_variants |
| `status` | Enum | Yes | queue/processing/done/error |
| `provider_task_id` | String(255) | Nullable | External API task ID |
| `provider_complete_time` | Timestamp | Nullable | Completion time |
| `provider_consume_credit` | Integer | Yes | Provider resource usage |
| `cost_credit` | Integer | Yes | Credits charged |
| `error` | Text | Nullable | Error message if failed |
| `prompt` | Text | Yes | User's prompt |
| `generation_params` | JSON | Yes | Generation parameters |
| `references_meta` | JSON | Nullable | Reference images metadata |
| `success_url_asset` | String(1024) | Nullable | Result URL |
| `telegram_file_id` | String(255) | Nullable | Telegram file ID |
| `created_at` | Timestamp | Yes | Creation time |

### Relationships

```
users 1──N payments
users 1──N transactions
users 1──N generations_job
providers 1──N ai_models
ai_models 1──N pricing_variants
pricing_variants 1──N generations_job
transactions N──1 payments (nullable)
transactions N──1 generations_job (nullable)
transactions N──1 credit_packages (nullable)
```

## Services

### Auth Service (`app/services/auth/`)

Validates Telegram Mini App InitData using HMAC-SHA256:
- Parses URL-encoded initData string
- Validates hash signature against bot token
- Checks auth_date freshness (configurable expiration)
- Extracts user data (TelegramUser model)

**Algorithm:**
1. Parse query string, extract `hash`
2. Build data-check-string (sorted key=value pairs, joined by `\n`)
3. Calculate `secret_key = HMAC-SHA256("WebAppData", bot_token)`
4. Calculate `hash = HMAC-SHA256(secret_key, data_check_string)`
5. Compare hashes (timing-safe)
6. Verify `auth_date` not older than `init_data_expire_seconds`

**Exceptions:**
- `MissingInitDataError` — empty or malformed initData
- `InvalidInitDataError` — hash validation failed
- `ExpiredInitDataError` — auth_date too old

### KIE API Service (`app/services/kie/`)

HTTP client for kie.ai API with:
- Task creation (`POST /api/v1/jobs/createTask`)
- Status polling (`GET /api/v1/jobs/recordInfo`)
- Adaptive polling intervals (3s → 10s → 15s)
- Custom exceptions for each HTTP error code
- Timeout handling with `KieTaskTimeoutError`

**States:** waiting → queuing → generating → success/fail

### Generation Service (`app/services/generation.py`)

Orchestrates the full generation lifecycle as a background task:

1. **Receive job** — load job with user, pricing variant, model, and provider from database
2. **Update status** — set job status to `processing`
3. **Send to KIE** — create task via KieService
4. **Poll for result** — wait with adaptive polling (3-15s intervals)
5. **On success:**
   - Update job status to `done`
   - Save result URL and completion time
   - Send image/video to user via Telegram bot
   - Store `telegram_file_id` for caching
6. **On error:**
   - Update job status to `error`
   - Create refund transaction (return credits)
   - Send error notification to user

**Entry point:** `process_generation(job_id)` — creates own DB session and bot instance.

**Error handling:**
- `KieTaskFailedError` → refund + error notification
- `KieTaskTimeoutError` → refund + timeout notification
- `KieAPIError` → refund + error notification

### Notification Service (`app/services/notification.py`)

Sends Telegram notifications to users:
- `send_generation_result(bot, chat_id, result_url, is_video)` — send image/video
- `send_generation_error(bot, chat_id, error_message, credits_refunded)` — error notification
- `send_generation_timeout(bot, chat_id, credits_refunded)` — timeout notification
- `send_payment_success(bot, chat_id, credits_added, new_balance)` — payment notification

## Repositories

### BaseRepository
Generic CRUD: `get_by_id()`, `get_all()`, `create()`, `update()`, `delete()`

### UserRepository
- `get_by_telegram_id(telegram_user_id)` — find user by Telegram ID
- `get_or_create(...)` — register new or return existing user
- `get_balance(user_id)` — calculate balance from transactions sum

### GenerationJobRepository
- `get_user_jobs(user_id, limit, offset)` — user's generation history
- `get_user_jobs_filtered(user_id, limit, offset)` — filtered history with eager-loaded pricing_variant → model → provider
- `get_pending_jobs(limit)` — jobs needing status poll (queue/processing)
- `get_by_provider_task_id(provider_task_id)` — find by external ID
- `get_by_id_for_processing(job_id)` — load job with user, pricing variant, model, and provider

### ProviderRepository
- `get_all_active_with_models()` — all active providers with active models and pricing variants
- `get_by_gen_type(gen_type)` — active providers filtered by "image"/"video"

### AiModelRepository
- `get_by_api_model_id(api_model_id)` — find model by API model ID
- `get_with_variants(model_id)` — single model with active pricing variants

### PricingVariantRepository
- `get_by_id_with_model(variant_id)` — variant with eager-loaded model and provider
- `get_active_by_model_id(model_id)` — active variants for a model

### CreditPackageRepository
- `get_active(limit, offset)` — active packages only
- `get_active_ordered_by_price()` — active packages sorted by price

### TransactionRepository
- `get_user_transactions(user_id, limit, offset)` — transaction history
- `get_by_type(user_id, tx_type)` — filter by type
- `create_deposit(...)` — create deposit transaction
- `create_withdrawal(...)` — create withdrawal (negative amount)
- `create_refund(...)` — create refund transaction

## API Layer (`app/api/`)

### Dependencies (`deps.py`)

**`get_db_session`** — async generator yielding SQLAlchemy session with auto-commit/rollback.

**`get_current_user`** — authenticates TMA requests:
1. Extracts initData from `Authorization: tma <initData>` header
2. Validates initData via auth service
3. Gets or creates user in database
4. Returns `User` model instance

**Type aliases:**
- `DBSession = Annotated[AsyncSession, Depends(get_db_session)]`
- `CurrentUser = Annotated[User, Depends(get_current_user)]`

### Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/me` | Required | User profile with balance |
| GET | `/api/providers` | Required | List providers with models and pricing variants |
| GET | `/api/packages` | Required | List active credit packages |
| POST | `/api/generations` | Required | Create new generation job |
| GET | `/api/generations` | Required | User's generation history |
| GET | `/api/generations/{id}` | Required | Generation job details |
| POST | `/webhook/telegram` | Secret Token | Telegram webhook (if enabled) |

### Webhook Endpoint

Available only when `WEBHOOK_ENABLED=true`. Receives updates from Telegram.

**Authentication:** `X-Telegram-Bot-Api-Secret-Token` header must match `WEBHOOK_SECRET`.

**Flow:**
1. Verify secret token
2. Parse Update JSON
3. Feed to aiogram dispatcher
4. Return 200 OK (even on errors to prevent retries)

### App Factory (`__init__.py`)

`create_app()` returns configured FastAPI instance with:
- CORS middleware (allow all origins for TMA iframe)
- Registered routers
- OpenAPI documentation at `/docs`
