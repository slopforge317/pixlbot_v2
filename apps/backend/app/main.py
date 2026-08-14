"""Application entry point."""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from api import create_app
from bot import create_bot, create_dispatcher, setup_bot_webhook, shutdown_bot_webhook
from core.config import settings
from core.logging import setup_logging
from fastapi import FastAPI
from loguru import logger
from services.funnel import funnel_message_loop, seed_funnel_steps
from services.generation import (
    kie_reconciliation_loop,
    validate_kie_callback_settings,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """FastAPI lifespan: startup and shutdown events."""
    setup_logging()
    logger.info("Starting pixlbot API...")
    validate_kie_callback_settings()

    if settings.funnel_enabled:
        await seed_funnel_steps()
        logger.info("Funnel steps seeded")
    else:
        logger.warning("Funnel messaging is disabled")

    # Setup bot webhook or polling
    if not settings.telegram_bot_enabled:
        logger.warning("Telegram bot runtime is disabled")
    elif settings.webhook_enabled:
        await setup_bot_webhook(app)
        logger.info("Bot running in webhook mode")
    else:
        # Run polling as background task
        bot = create_bot()
        dp = create_dispatcher()
        app.state.bot = bot
        app.state.dispatcher = dp
        app.state.polling_task = asyncio.create_task(dp.start_polling(bot))
        logger.info("Bot running in polling mode")

    if settings.kie_callback_enabled:
        app.state.kie_reconciliation_task = asyncio.create_task(
            kie_reconciliation_loop()
        )

    # Funnel messages require an active Telegram bot.
    if settings.telegram_bot_enabled and settings.funnel_enabled:
        app.state.funnel_task = asyncio.create_task(funnel_message_loop())

    yield

    reconciliation_task = getattr(app.state, "kie_reconciliation_task", None)
    if reconciliation_task:
        reconciliation_task.cancel()
        try:
            await reconciliation_task
        except asyncio.CancelledError:
            pass

    # Stop funnel message loop
    funnel_task = getattr(app.state, "funnel_task", None)
    if funnel_task:
        funnel_task.cancel()
        try:
            await funnel_task
        except asyncio.CancelledError:
            pass

    # Cleanup bot
    if not settings.telegram_bot_enabled:
        pass
    elif settings.webhook_enabled:
        await shutdown_bot_webhook(app)
    else:
        # Stop polling
        polling_task = getattr(app.state, "polling_task", None)
        if polling_task:
            polling_task.cancel()
            try:
                await polling_task
            except asyncio.CancelledError:
                pass
        bot = getattr(app.state, "bot", None)
        if bot:
            await bot.session.close()
        logger.info("Polling stopped")

    logger.info("pixlbot API stopped")


def create_application() -> FastAPI:
    """Create main FastAPI application with lifespan."""
    fastapi_app = create_app()
    fastapi_app.router.lifespan_context = lifespan
    return fastapi_app


# FastAPI app instance for uvicorn
app = create_application()


async def run_bot() -> None:
    """Run Telegram bot polling (standalone mode)."""
    setup_logging()
    logger.info("Starting pixlbot bot...")

    bot = create_bot()
    dp = create_dispatcher()

    logger.info("Bot is starting polling...")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        logger.info("pixlbot bot stopped")


if __name__ == "__main__":
    # For development: run bot only
    # Production: uvicorn main:app + separate bot process
    asyncio.run(run_bot())
