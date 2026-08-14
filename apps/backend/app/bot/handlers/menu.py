from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, Message
from bot.keyboards import balance_menu_keyboard, main_menu_keyboard
from bot.texts import BALANCE_MENU_TEXT, MENU_TEXT
from core.config import settings
from db.repositories.credit_package import CreditPackageRepository
from db.repositories.user import UserRepository
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

router = Router(name="menu")


@router.callback_query(F.data == "menu:balance")
async def on_balance(callback: CallbackQuery, session: AsyncSession) -> None:
    """Show balance with top-up submenu."""
    await callback.answer()
    msg = callback.message
    if not callback.from_user or not isinstance(msg, Message):
        return

    repo = UserRepository(session)
    user = await repo.get_by_telegram_id(callback.from_user.id)
    balance = 0
    if user:
        balance = await repo.get_balance(user.user_id)
    packages = await CreditPackageRepository(session).get_active_ordered_by_price()

    text = BALANCE_MENU_TEXT.format(
        credits=balance,
        pro_gens=balance // 5,
        basic_gens=balance // 2,
    )
    keyboard = balance_menu_keyboard(settings.tma_url, packages)
    try:
        await msg.edit_text(text, reply_markup=keyboard)
    except TelegramBadRequest as exc:
        logger.warning(
            f"Balance message edit failed, sending a new message: "
            f"telegram_user_id={callback.from_user.id}, error={exc}"
        )
        await msg.answer(text, reply_markup=keyboard)


@router.callback_query(F.data == "menu:back")
async def on_back(callback: CallbackQuery) -> None:
    """Return to main menu."""
    await callback.answer()
    msg = callback.message
    if not isinstance(msg, Message):
        return

    await msg.edit_text(
        MENU_TEXT,
        reply_markup=main_menu_keyboard(settings.tma_url),
    )


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
