from typing import TYPE_CHECKING

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TEST
from aiogram.enums import ParseMode
from bot.handlers import setup_routers
from bot.middlewares import DbSessionMiddleware
from core.config import settings
from db.session import async_session_maker
from loguru import logger

if TYPE_CHECKING:
    from fastapi import FastAPI


def create_bot() -> Bot:
    """Create and configure bot instance."""
    # Use Telegram Test Environment API if enabled
    session = None
    if settings.telegram_test_mode:
        session = AiohttpSession(api=TEST)
        logger.info("Using Telegram Test Environment API")

    return Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        session=session,
    )


def create_dispatcher() -> Dispatcher:
    """Create and configure dispatcher with middlewares and routers."""
    dp = Dispatcher()

    # Register middlewares
    dp.message.middleware(DbSessionMiddleware(async_session_maker))
    dp.callback_query.middleware(DbSessionMiddleware(async_session_maker))
    dp.pre_checkout_query.middleware(DbSessionMiddleware(async_session_maker))

    # Register routers
    dp.include_router(setup_routers())

    return dp


async def setup_bot_webhook(app: "FastAPI") -> None:
    """Setup bot and dispatcher for webhook mode.

    Creates bot and dispatcher instances, stores them in app.state,
    and registers webhook with Telegram.
    """
    bot = create_bot()
    dp = create_dispatcher()

    # Store in app state for access in webhook endpoint
    app.state.bot = bot
    app.state.dispatcher = dp

    # Build webhook URL
    webhook_url = f"{settings.webhook_base_url}{settings.webhook_path}"

    # Register webhook with Telegram
    await bot.set_webhook(
        url=webhook_url,
        secret_token=settings.webhook_secret,
        drop_pending_updates=True,
        allowed_updates=dp.resolve_used_update_types(),
    )
    logger.info(f"Webhook registered: {webhook_url}")


async def shutdown_bot_webhook(app: "FastAPI") -> None:
    """Cleanup bot on shutdown.

    Deletes webhook from Telegram and closes bot session.
    """
    bot = getattr(app.state, "bot", None)
    if bot is not None:
        try:
            await bot.delete_webhook()
            logger.info("Webhook deleted")
        except Exception as e:
            logger.error(f"Error deleting webhook: {e}")
        finally:
            await bot.session.close()
            logger.info("Bot session closed")


__all__ = [
    "create_bot",
    "create_dispatcher",
    "setup_bot_webhook",
    "shutdown_bot_webhook",
]
