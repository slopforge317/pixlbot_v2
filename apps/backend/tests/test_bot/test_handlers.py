from unittest.mock import ANY, AsyncMock, MagicMock

import pytest
from aiogram.filters import CommandObject
from aiogram.types import CallbackQuery, Message
from core.config import settings
from db.repositories.user import UserRepository
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.handlers.commands import cmd_start
from app.bot.handlers.menu import catch_all, on_back, on_balance
from app.bot.texts import (
    BALANCE_MENU_TEXT,
    MENU_TEXT,
    WELCOME_BACK,
    WELCOME_NEW,
)

# --- /start tests ---


@pytest.mark.asyncio
async def test_cmd_start_new_user(
    db_session: AsyncSession,
    mock_message: MagicMock,
    mock_command: CommandObject,
) -> None:
    """Test /start command creates new user and sends welcome message."""
    await cmd_start(mock_message, db_session, mock_command)

    # Verify welcome message for new user with reply_markup
    expected_text = WELCOME_NEW.format(bonus=settings.welcome_bonus_credits)
    mock_message.answer.assert_called_once_with(expected_text, reply_markup=ANY)

    # Verify user was created in database
    repo = UserRepository(db_session)
    user = await repo.get_by_telegram_id(mock_message.from_user.id)
    assert user is not None
    assert user.first_name == "Test"
    assert user.last_name == "User"
    assert user.username == "testuser"
    assert user.utm_source == "direct"


@pytest.mark.asyncio
async def test_cmd_start_existing_user(
    db_session: AsyncSession,
    mock_message: MagicMock,
    mock_command: CommandObject,
) -> None:
    """Test /start command for existing user sends welcome back message."""
    # First, create the user
    repo = UserRepository(db_session)
    user, _ = await repo.get_or_create(
        telegram_user_id=mock_message.from_user.id,
        chat_id=mock_message.chat.id,
        first_name=mock_message.from_user.first_name,
        last_name=mock_message.from_user.last_name,
        username=mock_message.from_user.username,
    )
    await db_session.commit()

    # Now call /start again
    await cmd_start(mock_message, db_session, mock_command)

    # Verify welcome back message with reply_markup
    expected_text = WELCOME_BACK.format(
        first_name=mock_message.from_user.first_name,
        pro_gens=0,
        basic_gens=0,
    )
    mock_message.answer.assert_called_once_with(expected_text, reply_markup=ANY)


@pytest.mark.asyncio
async def test_cmd_start_with_utm(
    db_session: AsyncSession,
    mock_message: MagicMock,
    mock_command_with_utm: CommandObject,
) -> None:
    """Test /start command with UTM parameter."""
    await cmd_start(mock_message, db_session, mock_command_with_utm)

    # Verify user was created with UTM source
    repo = UserRepository(db_session)
    user = await repo.get_by_telegram_id(mock_message.from_user.id)
    assert user is not None
    assert user.utm_source == "utm_google"


@pytest.mark.asyncio
async def test_cmd_start_no_from_user(
    db_session: AsyncSession,
    mock_command: CommandObject,
) -> None:
    """Test /start command with no from_user (edge case)."""
    mock_message = MagicMock()
    mock_message.from_user = None

    await cmd_start(mock_message, db_session, mock_command)

    # Should return early without calling answer
    mock_message.answer.assert_not_called()


# --- Callback handler tests ---


@pytest.fixture
def mock_callback(mock_message: MagicMock) -> MagicMock:
    """Create a mock CallbackQuery."""
    callback = MagicMock(spec=CallbackQuery)
    callback.from_user = mock_message.from_user
    callback.message = MagicMock(spec=Message)
    callback.message.edit_text = AsyncMock()
    callback.answer = AsyncMock()
    return callback


@pytest.mark.asyncio
async def test_on_balance(
    db_session: AsyncSession,
    mock_callback: MagicMock,
) -> None:
    """Test menu:balance callback shows balance with submenu."""
    # Create user first
    repo = UserRepository(db_session)
    await repo.get_or_create(
        telegram_user_id=mock_callback.from_user.id,
        chat_id=123456789,
        first_name=mock_callback.from_user.first_name,
    )
    await db_session.commit()

    await on_balance(mock_callback, db_session)

    expected_text = BALANCE_MENU_TEXT.format(pro_gens=0, basic_gens=0)
    mock_callback.message.edit_text.assert_called_once_with(
        expected_text, reply_markup=ANY
    )
    mock_callback.answer.assert_called_once()


@pytest.mark.asyncio
async def test_on_balance_unregistered_user(
    db_session: AsyncSession,
    mock_callback: MagicMock,
) -> None:
    """Test menu:balance callback for unregistered user shows zero balance."""
    await on_balance(mock_callback, db_session)

    expected_text = BALANCE_MENU_TEXT.format(pro_gens=0, basic_gens=0)
    mock_callback.message.edit_text.assert_called_once_with(
        expected_text, reply_markup=ANY
    )
    mock_callback.answer.assert_called_once()


@pytest.mark.asyncio
async def test_on_back(mock_callback: MagicMock) -> None:
    """Test menu:back callback returns to main menu."""
    await on_back(mock_callback)

    mock_callback.message.edit_text.assert_called_once_with(MENU_TEXT, reply_markup=ANY)
    mock_callback.answer.assert_called_once()


# --- Catch-all test ---


@pytest.mark.asyncio
async def test_catch_all(mock_message: MagicMock) -> None:
    """Test catch-all handler sends main menu."""
    await catch_all(mock_message)

    mock_message.answer.assert_called_once_with(MENU_TEXT, reply_markup=ANY)


@pytest.mark.asyncio
async def test_catch_all_no_from_user() -> None:
    """Test catch-all handler with no from_user (edge case)."""
    mock_message = MagicMock()
    mock_message.from_user = None

    await catch_all(mock_message)

    mock_message.answer.assert_not_called()
