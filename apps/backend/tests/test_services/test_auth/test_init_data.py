"""Unit tests for InitData validation service."""

import hashlib
import hmac
import json
import time
from unittest.mock import patch
from urllib.parse import urlencode

import pytest
from services.auth.exceptions import (
    ExpiredInitDataError,
    InvalidInitDataError,
    MissingInitDataError,
)
from services.auth.init_data import (
    _build_data_check_string,
    _calculate_hash,
    _parse_init_data,
    validate_init_data,
)

# Test bot token
TEST_BOT_TOKEN = "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"


def generate_init_data(
    bot_token: str,
    user_id: int = 123456789,
    first_name: str = "Test",
    last_name: str | None = "User",
    username: str | None = "testuser",
    auth_date: int | None = None,
    query_id: str | None = "AAHdF6IQAAAAAAN0XohGezM",
) -> str:
    """Generate valid initData for testing."""
    if auth_date is None:
        auth_date = int(time.time())

    user_data = {"id": user_id, "first_name": first_name}
    if last_name:
        user_data["last_name"] = last_name
    if username:
        user_data["username"] = username

    params = {
        "auth_date": str(auth_date),
        "user": json.dumps(user_data),
    }
    if query_id:
        params["query_id"] = query_id

    # Calculate hash
    data_check_string = _build_data_check_string(params)
    hash_value = _calculate_hash(data_check_string, bot_token)
    params["hash"] = hash_value

    return urlencode(params)


class TestBuildDataCheckString:
    """Tests for _build_data_check_string function."""

    def test_sorts_params_alphabetically(self):
        """Params should be sorted alphabetically by key."""
        params = {"z_key": "z_value", "a_key": "a_value", "m_key": "m_value"}
        result = _build_data_check_string(params)
        assert result == "a_key=a_value\nm_key=m_value\nz_key=z_value"

    def test_joins_with_newline(self):
        """Params should be joined with newline."""
        params = {"auth_date": "123", "user": "{}"}
        result = _build_data_check_string(params)
        assert "\n" in result
        assert result.count("\n") == 1

    def test_empty_params(self):
        """Empty params should return empty string."""
        result = _build_data_check_string({})
        assert result == ""


class TestCalculateHash:
    """Tests for _calculate_hash function."""

    def test_returns_hex_string(self):
        """Hash should be a hex string."""
        result = _calculate_hash("test_data", TEST_BOT_TOKEN)
        assert isinstance(result, str)
        assert all(c in "0123456789abcdef" for c in result)

    def test_hash_length(self):
        """SHA256 hex should be 64 characters."""
        result = _calculate_hash("test_data", TEST_BOT_TOKEN)
        assert len(result) == 64

    def test_same_input_same_hash(self):
        """Same input should produce same hash."""
        result1 = _calculate_hash("test_data", TEST_BOT_TOKEN)
        result2 = _calculate_hash("test_data", TEST_BOT_TOKEN)
        assert result1 == result2

    def test_different_input_different_hash(self):
        """Different input should produce different hash."""
        result1 = _calculate_hash("data1", TEST_BOT_TOKEN)
        result2 = _calculate_hash("data2", TEST_BOT_TOKEN)
        assert result1 != result2

    def test_uses_webappdata_key(self):
        """Should use 'WebAppData' as key for secret derivation."""
        data = "test"
        secret_key = hmac.new(
            key=b"WebAppData",
            msg=TEST_BOT_TOKEN.encode(),
            digestmod=hashlib.sha256,
        ).digest()
        expected = hmac.new(
            key=secret_key,
            msg=data.encode(),
            digestmod=hashlib.sha256,
        ).hexdigest()

        result = _calculate_hash(data, TEST_BOT_TOKEN)
        assert result == expected


class TestParseInitData:
    """Tests for _parse_init_data function."""

    def test_parses_url_encoded_string(self):
        """Should parse URL-encoded query string."""
        raw = "auth_date=123&user=%7B%22id%22%3A1%7D"
        result = _parse_init_data(raw)
        assert result["auth_date"] == "123"
        assert result["user"] == '{"id":1}'

    def test_handles_special_characters(self):
        """Should handle URL-encoded special characters."""
        raw = "key=value%20with%20spaces"
        result = _parse_init_data(raw)
        assert result["key"] == "value with spaces"


class TestValidateInitData:
    """Tests for validate_init_data function."""

    @patch("services.auth.init_data.settings")
    def test_valid_init_data(self, mock_settings):
        """Valid initData should return TelegramInitData."""
        mock_settings.bot_token = TEST_BOT_TOKEN
        mock_settings.init_data_expire_seconds = 3600

        init_data = generate_init_data(TEST_BOT_TOKEN)
        result = validate_init_data(init_data)

        assert result.user.id == 123456789
        assert result.user.first_name == "Test"
        assert result.user.last_name == "User"
        assert result.user.username == "testuser"

    @patch("services.auth.init_data.settings")
    def test_empty_init_data_raises(self, mock_settings):
        """Empty initData should raise MissingInitDataError."""
        mock_settings.bot_token = TEST_BOT_TOKEN

        with pytest.raises(MissingInitDataError, match="empty"):
            validate_init_data("")

    @patch("services.auth.init_data.settings")
    def test_missing_hash_raises(self, mock_settings):
        """Missing hash should raise MissingInitDataError."""
        mock_settings.bot_token = TEST_BOT_TOKEN

        init_data = "auth_date=123&user=%7B%22id%22%3A1%7D"
        with pytest.raises(MissingInitDataError, match="hash"):
            validate_init_data(init_data)

    @patch("services.auth.init_data.settings")
    def test_invalid_hash_raises(self, mock_settings):
        """Invalid hash should raise InvalidInitDataError."""
        mock_settings.bot_token = TEST_BOT_TOKEN
        mock_settings.init_data_expire_seconds = 3600

        init_data = generate_init_data(TEST_BOT_TOKEN)
        # Corrupt the hash
        init_data = init_data.replace("hash=", "hash=invalid")

        with pytest.raises(InvalidInitDataError):
            validate_init_data(init_data)

    @patch("services.auth.init_data.settings")
    def test_expired_init_data_raises(self, mock_settings):
        """Expired initData should raise ExpiredInitDataError."""
        mock_settings.bot_token = TEST_BOT_TOKEN
        mock_settings.init_data_expire_seconds = 3600

        old_auth_date = int(time.time()) - 7200  # 2 hours ago
        init_data = generate_init_data(TEST_BOT_TOKEN, auth_date=old_auth_date)

        with pytest.raises(ExpiredInitDataError):
            validate_init_data(init_data)

    @patch("services.auth.init_data.settings")
    def test_missing_auth_date_raises(self, mock_settings):
        """Missing auth_date should raise MissingInitDataError."""
        mock_settings.bot_token = TEST_BOT_TOKEN

        # Build initData without auth_date
        user_data = json.dumps({"id": 123, "first_name": "Test"})
        params = {"user": user_data}
        data_check_string = _build_data_check_string(params)
        hash_value = _calculate_hash(data_check_string, TEST_BOT_TOKEN)
        params["hash"] = hash_value
        init_data = urlencode(params)

        with pytest.raises(MissingInitDataError, match="auth_date"):
            validate_init_data(init_data)

    @patch("services.auth.init_data.settings")
    def test_missing_user_raises(self, mock_settings):
        """Missing user should raise MissingInitDataError."""
        mock_settings.bot_token = TEST_BOT_TOKEN
        mock_settings.init_data_expire_seconds = 3600

        # Build initData without user
        params = {"auth_date": str(int(time.time()))}
        data_check_string = _build_data_check_string(params)
        hash_value = _calculate_hash(data_check_string, TEST_BOT_TOKEN)
        params["hash"] = hash_value
        init_data = urlencode(params)

        with pytest.raises(MissingInitDataError, match="user"):
            validate_init_data(init_data)

    @patch("services.auth.init_data.settings")
    def test_invalid_user_json_raises(self, mock_settings):
        """Invalid user JSON should raise MissingInitDataError."""
        mock_settings.bot_token = TEST_BOT_TOKEN
        mock_settings.init_data_expire_seconds = 3600

        # Build initData with invalid user JSON
        params = {"auth_date": str(int(time.time())), "user": "not-json"}
        data_check_string = _build_data_check_string(params)
        hash_value = _calculate_hash(data_check_string, TEST_BOT_TOKEN)
        params["hash"] = hash_value
        init_data = urlencode(params)

        with pytest.raises(MissingInitDataError, match="user"):
            validate_init_data(init_data)

    @patch("services.auth.init_data.settings")
    def test_user_without_required_fields_raises(self, mock_settings):
        """User without required fields should raise MissingInitDataError."""
        mock_settings.bot_token = TEST_BOT_TOKEN
        mock_settings.init_data_expire_seconds = 3600

        # Build initData with incomplete user
        params = {
            "auth_date": str(int(time.time())),
            "user": json.dumps({"id": 123}),  # missing first_name
        }
        data_check_string = _build_data_check_string(params)
        hash_value = _calculate_hash(data_check_string, TEST_BOT_TOKEN)
        params["hash"] = hash_value
        init_data = urlencode(params)

        with pytest.raises(MissingInitDataError, match="user"):
            validate_init_data(init_data)

    @patch("services.auth.init_data.settings")
    def test_parses_optional_fields(self, mock_settings):
        """Should parse optional fields when present."""
        mock_settings.bot_token = TEST_BOT_TOKEN
        mock_settings.init_data_expire_seconds = 3600

        init_data = generate_init_data(
            TEST_BOT_TOKEN,
            query_id="test_query_id",
        )
        result = validate_init_data(init_data)

        assert result.query_id == "test_query_id"
