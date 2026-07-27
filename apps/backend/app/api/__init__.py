"""FastAPI application factory."""

from api.middleware import RequestLoggingMiddleware
from api.routes import (
    generations_router,
    packages_router,
    payments_router,
    providers_router,
    storage_router,
    users_router,
    webhook_router,
)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title="pixlbot API",
        description="Backend API for pixlbot TMA",
        version="0.1.0",
    )

    @app.get("/health")
    async def health_check() -> dict[str, str]:
        """Health check endpoint for Docker/k8s."""
        return {"status": "ok"}

    # Request logging middleware (must be added first to wrap all requests)
    app.add_middleware(RequestLoggingMiddleware)

    # CORS middleware for TMA
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # TMA runs in iframe, origin varies
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(users_router)
    app.include_router(providers_router)
    app.include_router(generations_router)
    app.include_router(packages_router)
    app.include_router(payments_router)
    app.include_router(storage_router)

    # Webhook router: always include (YooKassa needs it even without Telegram webhooks)
    app.include_router(webhook_router)

    return app
