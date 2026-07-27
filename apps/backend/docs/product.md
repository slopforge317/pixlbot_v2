# Product Overview

## Project Name
**pixlbot** — Telegram Mini App (TMA) + backend for AI image/video generation via multiple neural networks with credit-based monetization.

## Core Value Proposition
Open Mini App → select model → enter prompt (+ references) → receive result in Telegram chat, with transparent credit-based pricing.

## Target Audience
Users who need quick access to multiple generative AI models in one place without switching between different services.

## Architecture Overview

### Telegram Mini App (TMA) — Primary Interface
All user interactions happen in the Mini App:
- Model selection and configuration
- Prompt input with reference images
- Generation history browsing
- Credit balance and purchase
- Account settings

### Telegram Bot — Notifications Only
The bot serves as a delivery channel:
- Sends ready images/videos to chat
- Notifies about generation status (success/error)
- Payment confirmations
- `/start` command opens the Mini App

## Features

### Image Generation
- **Models:** Nano Banana Pro, Seedream 4.5, GPT Image 1.5
- **Generation types:** Text-to-Image, Image-to-Image, Edit
- **Parameters:** Aspect ratio, quality level, resolution, output format
- **Interface:** TMA web UI

### Video Generation
- **Models:** Veo 3.1, Kling 2.6, Sora 2 Pro
- **Generation types:** Text-to-Video, Image-to-Video, Reference-to-Video
- **Parameters:** Aspect ratio, quality/size, duration, sound

### Credit System
- Users purchase credit packages (in TMA)
- Each generation costs credits (varies by model/mode)
- Balance calculated from transaction history (immutable ledger)
- Refunds on generation errors

### User Flow
1. User opens bot → `/start` → Mini App launches
2. In TMA: select model, enter prompt, configure parameters
3. Submit generation request
4. Bot sends notification when ready + result media
5. User can view history, balance, buy credits — all in TMA

## Monetization

### Credit Packages
Predefined packages with:
- Name (e.g., "Starter", "Pro")
- Credit amount
- Fiat price (stored in kopecks)
- Active/inactive status

### Pricing Model
- Each model mode has a fixed credit price
- Different quality levels = different prices (three-tier hierarchy: Model → Quality tier → Generation type)
- No subscription, pay-as-you-go

## Technical Constraints

### Media Storage
- **No self-hosted storage** — results stored as KIE.ai URLs
- URLs expire after ~24 hours
- Media sent to user in Telegram chat
- `telegram_file_id` saved for re-sending

### Content Policy
- No NSFW filter in MVP
- Disclaimer shown to users
- All prompts and errors logged

## Current Status (MVP)

### Completed
- [x] Database models (all 7 tables) with three-tier model hierarchy
- [x] All repositories (User, GenerationJob, Provider, AIModel, PricingVariant, CreditPackage, Transaction)
- [x] KIE API client with polling
- [x] Configuration system
- [x] Logging setup
- [x] Bot basic commands (/start, /help, /balance)
- [x] FastAPI app with CORS
- [x] Telegram InitData authentication (HMAC-SHA256)
- [x] `GET /api/me` endpoint (user profile + balance)
- [x] `GET /api/providers` endpoint (list providers with models and pricing variants)
- [x] `GET /api/packages` endpoint (credit packages for purchase)
- [x] `POST /api/generations` endpoint (create generation)
- [x] `GET /api/generations` endpoint (generation history)
- [x] `GET /api/generations/{id}` endpoint (generation details)
- [x] Generation service (balance check, credit deduction, KIE integration, refunds)
- [x] Bot notifications (generation ready, errors, timeouts)
- [x] Seed data for 7 AI models (3 video + 4 image) with full api_config

### Planned
- [ ] TMA frontend (separate project)
- [ ] Payment integration
