"""Telegram Mini App InitData validation service."""

import hashlib
import hmac
import json
import time
from urllib.parse import parse_qs, unquote

from api.schemas.auth import TelegramInitData, TelegramUser
from core.config import settings
from loguru import logger
from services.auth.exceptions import (
    ExpiredInitDataError,
    InvalidInitDataError,
    MissingInitDataError,
)


def validate_init_data(init_data_raw: str) -> TelegramInitData:
    """
    Validate Telegram Mini App InitData.

    Algorithm:
    1. Parse URL-encoded query string
    2. Extract and remove 'hash' parameter
    3. Build data-check-string (sorted key=value pairs joined by \\n)
    4. Calculate HMAC-SHA256 with secret derived from bot token
    5. Compare hashes (timing-safe)
    6. Check auth_date freshness
    7. Parse and return structured data

    Args:
        init_data_raw: URL-encoded initData string from TMA

    Raises:
        MissingInitDataError: If initData is empty or missing required fields
        InvalidInitDataError: If hash validation fails
        ExpiredInitDataError: If auth_date is too old

    Returns:
        TelegramInitData with parsed user data
    """
    logger.debug("Starting initData validation")

    if not init_data_raw:
        logger.warning("Validation failed: initData is empty")
        raise MissingInitDataError("InitData is empty")

    # Parse query string
    try:
        params = _parse_init_data(init_data_raw)
    except ValueError as e:
        raise MissingInitDataError(f"Failed to parse initData: {e}")

    # Extract hash
    received_hash = params.pop("hash", None)
    if not received_hash:
        raise MissingInitDataError("Missing hash in initData")

    # Build data-check-string and calculate hash
    data_check_string = _build_data_check_string(params)
    calculated_hash = _calculate_hash(data_check_string, settings.bot_token)

    # Timing-safe comparison
    if not hmac.compare_digest(calculated_hash, received_hash):
        logger.warning("Validation failed: hash mismatch")
        raise InvalidInitDataError("Hash validation failed")

    # Check auth_date freshness
    auth_date_str = params.get("auth_date")
    if not auth_date_str:
        raise MissingInitDataError("Missing auth_date in initData")

    try:
        auth_date = int(auth_date_str)
    except ValueError:
        raise MissingInitDataError("Invalid auth_date format")

    current_time = int(time.time())
    age_seconds = current_time - auth_date
    if age_seconds > settings.init_data_expire_seconds:
        logger.warning(
            f"Validation failed: initData expired "
            f"(auth_date={auth_date}, age={age_seconds}s, "
            f"max_age={settings.init_data_expire_seconds}s)"
        )
        raise ExpiredInitDataError(
            f"InitData expired: auth_date={auth_date}, "
            f"current_time={current_time}, "
            f"max_age={settings.init_data_expire_seconds}s"
        )

    # Parse user data
    user_json = params.get("user")
    if not user_json:
        raise MissingInitDataError("Missing user in initData")

    try:
        user_data = json.loads(user_json)
        user = TelegramUser(**user_data)
    except (json.JSONDecodeError, ValueError) as e:
        raise MissingInitDataError(f"Invalid user data: {e}")

    logger.info(
        f"InitData validated: telegram_user_id={user.id}, "
        f"username={user.username or 'none'}"
    )

    return TelegramInitData(
        query_id=params.get("query_id"),
        user=user,
        auth_date=auth_date,
        hash=received_hash,
        chat_type=params.get("chat_type"),
        chat_instance=params.get("chat_instance"),
        start_param=params.get("start_param"),
    )


def _parse_init_data(init_data_raw: str) -> dict[str, str]:
    """
    Parse URL-encoded initData string into dict.

    Args:
        init_data_raw: URL-encoded query string

    Returns:
        Dict with parsed key-value pairs
    """
    decoded = unquote(init_data_raw)
    parsed = parse_qs(decoded, keep_blank_values=True)
    # parse_qs returns lists, we need single values
    return {k: v[0] if v else "" for k, v in parsed.items()}


def _build_data_check_string(params: dict[str, str]) -> str:
    """
    Build sorted data-check-string from params (excluding hash).

    Args:
        params: Dict of initData parameters (hash already removed)

    Returns:
        Sorted key=value pairs joined by newline
    """
    sorted_params = sorted(params.items(), key=lambda x: x[0])
    return "\n".join(f"{k}={v}" for k, v in sorted_params)


def _calculate_hash(data_check_string: str, bot_token: str) -> str:
    """
    Calculate HMAC-SHA256 hash for InitData validation.

    Args:
        data_check_string: Sorted key=value pairs joined by newline
        bot_token: Telegram bot token

    Returns:
        Hex-encoded HMAC-SHA256 hash
    """
    # Step 1: Create secret key from bot token
    secret_key = hmac.new(
        key=b"WebAppData",
        msg=bot_token.encode(),
        digestmod=hashlib.sha256,
    ).digest()

    # Step 2: Calculate hash of data-check-string
    return hmac.new(
        key=secret_key,
        msg=data_check_string.encode(),
        digestmod=hashlib.sha256,
    ).hexdigest()
