"""User API schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class UserResponse(BaseModel):
    """User profile response for TMA."""

    user_id: int
    telegram_user_id: int
    first_name: str
    last_name: Optional[str]
    username: Optional[str]
    balance: int
    created_at: datetime

    model_config = {"from_attributes": True}


class UserBalanceResponse(BaseModel):
    """Quick balance check response."""

    balance: int
