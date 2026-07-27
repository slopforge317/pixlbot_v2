# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

pixlbot — Backend (FastAPI + Bot) for Telegram Mini App (TMA) that provides AI image/video generation via kei.ai API with credit-based monetization.

**Architecture:**
- **TMA (separate project)** — all UI/UX: model selection, prompts, history, balance, payments
- **FastAPI Backend** — REST API for TMA, generation orchestration, payments
- **Telegram Bot** — notifications only: sends ready images/videos, status updates

## Commands

**IMPORTANT:** All Python commands run through Poetry with `PYTHONPATH=app`:

```bash
# Tests
PYTHONPATH=app poetry run pytest -q              # All tests
PYTHONPATH=app poetry run pytest tests/test_file.py::test_name -v  # Single test

# Code quality (run STRICTLY IN ORDER)
PYTHONPATH=app poetry run isort .    # 1. Sort imports
PYTHONPATH=app poetry run black .    # 2. Format code
PYTHONPATH=app poetry run flake8 .   # 3. Check style
poetry run pyright                   # 4. Check types

# Run scripts
PYTHONPATH=app poetry run python <script>
```

## Workflow

### Task Complexity Definition
A task is **complex** if it involves:
- Multiple components/modules
- Integration with external APIs
- Architectural decisions
- Security/performance concerns

### Execution Protocol
1. **Read documentation** — all files in `docs/` before starting work
2. **Analyze** — dependencies, affected code, tests
3. **Complex task** → create plan in `plans/###-description.md`, wait for approval
4. **Simple task** → implement directly
5. **After implementation:**
   - Complex: full test suite + update `docs/test-summary.md`
   - Simple: only necessary checks
   - Commit with clear message

ALWAYS!!! **Do commit after each completed task with a clear message.**

### Self-Review Checklist (complex tasks)
- [ ] `PYTHONPATH=app poetry run pytest -q` passes
- [ ] `PYTHONPATH=app poetry run isort .` — imports sorted
- [ ] `PYTHONPATH=app poetry run black .` — code formatted
- [ ] `PYTHONPATH=app poetry run flake8 .` — no style violations
- [ ] `poetry run pyright` — no type errors
- [ ] Documentation updated when changing API/architecture

## Architecture

**Pattern:** Ports and Adapters — designed for easy swapping of DB (SQLite → PostgreSQL) and AI providers.

**Structure:**
```
app/
├── api/       # FastAPI endpoints (primary interface for TMA)
├── bot/       # aiogram handlers (notifications only)
├── services/  # generation logic, AI API clients, notifications
├── db/        # SQLAlchemy models, session, repositories
├── core/      # config, logging, shared infra
└── main.py
```

**Component responsibilities:**
- `api/` — REST API for TMA, Telegram InitData auth
- `bot/` — /start command, sending media/notifications to users
- `services/` — business logic, KIE API client, notification triggers

**Database principles:**
- All monetary values as integers (no floats)
- Immutable ledger for transactions (INSERT only)
- JSON fields for flexible provider configs

## Documentation

Before any task, read all files in `docs/`:
- `docs/structure.md` — architecture, DB schema
- `docs/tech.md` — stack and versions
- `docs/product.md` — features and domains
- `docs/testing.md` — test patterns
- `docs/test-summary.md` — current test state

Update relevant docs when changing architecture, APIs, or features.

## Code Markers

Use `AICODE-*:` comments for cross-agent memory:
- `AICODE-NOTE:` — non-obvious code explanations
- `AICODE-TODO:` — future work outside current scope
- `AICODE-QUESTION:` — needs human decision

## Plans

Complex tasks require a plan file in `plans/###-description.md` with: objective, steps, risks, rollback strategy. Wait for approval before implementation.

**CRITICAL — Naming convention:**
1. **FIRST** run `ls plans/` to see all existing plan files
2. Find the highest existing plan number (e.g., `006-*.md`)
3. New plan number = highest + 1 (e.g., `007-*.md`)
4. **NEVER** assume or guess the next number without checking!

Example: If `plans/` contains `001-*.md` through `006-*.md`, the next plan MUST be `007-description.md`.

## MCP Tools

Use `context7` MCP server to fetch up-to-date documentation for libraries (aiogram, FastAPI, SQLAlchemy, etc.) when needed.
