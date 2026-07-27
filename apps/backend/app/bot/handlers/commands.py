from aiogram import Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.types import Message
from bot.keyboards import main_menu_keyboard
from bot.texts import WELCOME_BACK, WELCOME_NEW
from core.config import settings
from db.enums import FunnelTriggerEvent
from db.repositories.transaction import TransactionRepository
from db.repositories.user import UserRepository
from loguru import logger
from services.funnel import fire_trigger
from sqlalchemy.ext.asyncio import AsyncSession

router = Router(name="commands")


@router.message(CommandStart())
async def cmd_start(
    message: Message,
    session: AsyncSession,
    command: CommandObject,
) -> None:
    """Handle /start command - register user and send welcome message."""
    if not message.from_user:
        return

    # Extract UTM from deep link (e.g., /start utm_google)
    utm_source = "direct"
    if command.args:
        utm_source = command.args

    logger.info(
        f"/start command: telegram_user_id={message.from_user.id}, "
        f"chat_id={message.chat.id}, utm_source={utm_source}"
    )

    repo = UserRepository(session)
    user, created = await repo.get_or_create(
        telegram_user_id=message.from_user.id,
        chat_id=message.chat.id,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
        username=message.from_user.username,
        utm_source=utm_source,
    )

    keyboard = main_menu_keyboard(settings.tma_url)

    if created:
        logger.info(
            f"New user registered: user_id={user.user_id}, "
            f"telegram_user_id={message.from_user.id}"
        )
        if settings.welcome_bonus_credits > 0:
            tx_repo = TransactionRepository(session)
            await tx_repo.create_bonus(
                user_id=user.user_id,
                amount_credits=settings.welcome_bonus_credits,
            )
        await fire_trigger(
            session, FunnelTriggerEvent.user_registered, user.user_id, user.chat_id
        )
        await session.commit()
        await message.answer(
            WELCOME_NEW.format(bonus=settings.welcome_bonus_credits),
            reply_markup=keyboard,
        )
    else:
        logger.debug(f"Existing user returned: user_id={user.user_id}")
        balance = await repo.get_balance(user.user_id)
        text = WELCOME_BACK.format(
            first_name=message.from_user.first_name,
            pro_gens=balance // 5,
            basic_gens=balance // 2,
        )
        await message.answer(text, reply_markup=keyboard)
