#!/usr/bin/env python3
"""
Generate valid Telegram initData for development/testing.

Usage:
    PYTHONPATH=app poetry run python scripts/generate_init_data.py

The output can be used as VITE_MOCK_INIT_DATA in frontend/dev/test env.
"""

import hashlib
import hmac
import time
import urllib.parse

from core.config import settings


def generate_init_data(
    user_id: int = 123456789,
    first_name: str = "Dev",
    last_name: str = "User",
    username: str = "devuser",
) -> str:
    """Generate valid initData string signed with BOT_TOKEN."""

    auth_date = int(time.time())

    # User data as JSON
    user_json = (
        f'{{"id":{user_id},'
        f'"first_name":"{first_name}",'
        f'"last_name":"{last_name}",'
        f'"username":"{username}",'
        f'"language_code":"ru"}}'
    )

    # Data pairs (must be sorted alphabetically for hash)
    data_pairs = {
        "auth_date": str(auth_date),
        "user": user_json,
    }

    # Create data-check-string (sorted, newline-separated)
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(data_pairs.items()))

    # Calculate hash
    secret_key = hmac.new(
        b"WebAppData", settings.bot_token.encode(), hashlib.sha256
    ).digest()

    hash_value = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()

    # Build initData string (URL-encoded)
    data_pairs["hash"] = hash_value

    init_data = "&".join(
        f"{k}={urllib.parse.quote(str(v), safe='')}" for k, v in data_pairs.items()
    )

    return init_data


if __name__ == "__main__":
    init_data = generate_init_data()

    print("=" * 60)
    print("Generated initData for development:")
    print("=" * 60)
    print()
    print(init_data)
    print()
    print("=" * 60)
    print("Add to frontend/.env.development or tma-backend/.env.test:")
    print("=" * 60)
    print()
    print(f"VITE_MOCK_INIT_DATA={init_data}")
    print()
