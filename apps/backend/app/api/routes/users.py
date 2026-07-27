"""User API endpoints."""

from api.deps import CurrentUser, DBSession
from api.schemas.user import UserResponse
from db.repositories.user import UserRepository
from fastapi import APIRouter
from loguru import logger

router = APIRouter(prefix="/api", tags=["users"])


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    user: CurrentUser,
    session: DBSession,
) -> UserResponse:
    """
    Get current user profile with balance.

    Requires: Authorization: tma <initData>
    """
    logger.debug(f"Getting user profile: user_id={user.user_id}")
    user_repo = UserRepository(session)
    balance = await user_repo.get_balance(user.user_id)

    return UserResponse(
        user_id=user.user_id,
        telegram_user_id=user.telegram_user_id,
        first_name=user.first_name,
        last_name=user.last_name,
        username=user.username,
        balance=balance,
        created_at=user.created_at,
    )
