import os
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.filters import CommandObject
from aiogram.types import Chat, Message, User
from db.base import Base
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# PostgreSQL test database URL
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://pixlbot:pixlbot_test@localhost:5432/pixlbot_pytest",
)


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create PostgreSQL database session for testing."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
def mock_user() -> User:
    """Create a mock Telegram user."""
    return User(
        id=123456789,
        is_bot=False,
        first_name="Test",
        last_name="User",
        username="testuser",
    )


@pytest.fixture
def mock_chat() -> Chat:
    """Create a mock Telegram chat."""
    return Chat(
        id=123456789,
        type="private",
    )


@pytest.fixture
def mock_message(mock_user: User, mock_chat: Chat) -> MagicMock:
    """Create a mock Message with answer method."""
    message = MagicMock(spec=Message)
    message.from_user = mock_user
    message.chat = mock_chat
    message.text = "hello"
    message.answer = AsyncMock()
    return message


@pytest.fixture
def mock_command() -> CommandObject:
    """Create a mock CommandObject with no arguments."""
    return CommandObject(command="start", prefix="/", args=None)


@pytest.fixture
def mock_command_with_utm() -> CommandObject:
    """Create a mock CommandObject with UTM parameter."""
    return CommandObject(command="start", prefix="/", args="utm_google")
