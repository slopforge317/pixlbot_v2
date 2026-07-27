from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from bot.keyboards import balance_menu_keyboard, main_menu_keyboard
from bot.texts import BALANCE_MENU_TEXT, MENU_TEXT
from core.config import settings
from db.repositories.user import UserRepository
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

router = Router(name="menu")


@router.callback_query(F.data == "menu:balance")
async def on_balance(callback: CallbackQuery, session: AsyncSession) -> None:
    """Show balance with top-up submenu."""
    msg = callback.message
    if not callback.from_user or not isinstance(msg, Message):
        return

    repo = UserRepository(session)
    user = await repo.get_by_telegram_id(callback.from_user.id)
    balance = 0
    if user:
        balance = await repo.get_balance(user.user_id)

    await msg.edit_text(
        BALANCE_MENU_TEXT.format(pro_gens=balance // 5, basic_gens=balance // 2),
        reply_markup=balance_menu_keyboard(settings.tma_url),
    )
    await callback.answer()


@router.callback_query(F.data == "menu:back")
async def on_back(callback: CallbackQuery) -> None:
    """Return to main menu."""
    msg = callback.message
    if not isinstance(msg, Message):
        return

    await msg.edit_text(
        MENU_TEXT,
        reply_markup=main_menu_keyboard(settings.tma_url),
    )
    await callback.answer()


@router.message()
async def catch_all(message: Message) -> None:
    """Reply with main menu to any unhandled text message."""
    if not message.from_user:
        return

    logger.debug(
        f"Catch-all message: telegram_user_id={message.from_user.id}, "
        f"text={message.text!r}"
    )
    await message.answer(
        MENU_TEXT,
        reply_markup=main_menu_keyboard(settings.tma_url),
    )
