"""Telegram InitData schemas."""

from typing import Optional

from pydantic import BaseModel


class TelegramUser(BaseModel):
    """User data from Telegram InitData."""

    id: int
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    language_code: Optional[str] = None
    is_premium: Optional[bool] = None
    photo_url: Optional[str] = None


class TelegramInitData(BaseModel):
    """Parsed and validated Telegram InitData."""

    query_id: Optional[str] = None
    user: TelegramUser
    auth_date: int
    hash: str
    chat_type: Optional[str] = None
    chat_instance: Optional[str] = None
    start_param: Optional[str] = None
