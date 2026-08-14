from aiogram import Router
from bot.handlers.commands import router as commands_router
from bot.handlers.menu import router as menu_router
from bot.handlers.payments import router as payments_router


def setup_routers() -> Router:
    """Setup all routers and return main router."""
    router = Router()
    router.include_router(commands_router)  # /start — first (priority)
    router.include_router(payments_router)  # invoices before message catch-all
    router.include_router(menu_router)  # callbacks + catch-all — last
    return router


__all__ = ["setup_routers"]
