"""FastAPI dependencies."""

from collections.abc import AsyncGenerator
from typing import Annotated

from core.config import settings
from core.logging import set_user_id
from db.models import User
from db.repositories.transaction import TransactionRepository
from db.repositories.user import UserRepository
from db.session import async_session_maker
from fastapi import Depends, Header, HTTPException, status
from loguru import logger
from services.auth import (
    AuthError,
    ExpiredInitDataError,
    InvalidInitDataError,
    validate_init_data,
)
from sqlalchemy.ext.asyncio import AsyncSession


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for database session."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


DBSession = Annotated[AsyncSession, Depends(get_db_session)]


async def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
    session: AsyncSession = Depends(get_db_session),
) -> User:
    """
    Authenticate user via Telegram InitData.

    Expected header format: Authorization: tma <initData>

    1. Extract initData from Authorization header
    2. Validate initData signature and freshness
    3. Get or create user in database
    4. Return User object

    Raises:
        HTTPException 401: Missing or invalid Authorization header
        HTTPException 401: Invalid initData signature
        HTTPException 401: Expired initData
    """
    if not authorization or not authorization.startswith("tma "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
            headers={"WWW-Authenticate": "tma"},
        )

    init_data_raw = authorization[4:]  # Remove "tma " prefix

    try:
        init_data = validate_init_data(init_data_raw)
    except InvalidInitDataError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid initData signature",
        )
    except ExpiredInitDataError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="InitData expired",
        )
    except AuthError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )

    # Get or create user
    user_repo = UserRepository(session)
    user, created = await user_repo.get_or_create(
        telegram_user_id=init_data.user.id,
        chat_id=init_data.user.id,  # In TMA context, chat_id = user_id
        first_name=init_data.user.first_name,
        last_name=init_data.user.last_name,
        username=init_data.user.username,
    )

    if created and settings.welcome_bonus_credits > 0:
        tx_repo = TransactionRepository(session)
        await tx_repo.create_bonus(
            user_id=user.user_id,
            amount_credits=settings.welcome_bonus_credits,
        )
        logger.info(
            f"Welcome bonus granted: user_id={user.user_id}, "
            f"credits={settings.welcome_bonus_credits}"
        )

    # Set user context for logging
    set_user_id(user.user_id)
    logger.debug(f"User context set: user_id={user.user_id}")

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
