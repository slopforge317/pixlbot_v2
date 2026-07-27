"""Integration tests for authentication."""

from unittest.mock import patch

import pytest
from core.config import settings
from httpx import AsyncClient

from tests.test_api.conftest import TEST_BOT_TOKEN


class TestAuthEndpoint:
    """Tests for authentication via /api/me endpoint."""

    @pytest.mark.asyncio
    @patch("services.auth.init_data.settings")
    async def test_valid_auth_returns_user(
        self, mock_settings, client: AsyncClient, valid_init_data: str
    ):
        """Valid initData should return user profile."""
        mock_settings.bot_token = TEST_BOT_TOKEN
        mock_settings.init_data_expire_seconds = 3600

        response = await client.get(
            "/api/me",
            headers={"Authorization": f"tma {valid_init_data}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["telegram_user_id"] == 123456789
        assert data["first_name"] == "Test"
        assert data["last_name"] == "User"
        assert data["username"] == "testuser"
        assert data["balance"] == settings.welcome_bonus_credits
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_missing_auth_header_returns_401(self, client: AsyncClient):
        """Missing Authorization header should return 401."""
        response = await client.get("/api/me")

        assert response.status_code == 401
        assert "Missing or invalid" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_invalid_auth_scheme_returns_401(self, client: AsyncClient):
        """Invalid auth scheme should return 401."""
        response = await client.get(
            "/api/me",
            headers={"Authorization": "Bearer some_token"},
        )

        assert response.status_code == 401
        assert "Missing or invalid" in response.json()["detail"]

    @pytest.mark.asyncio
    @patch("services.auth.init_data.settings")
    async def test_invalid_hash_returns_401(
        self, mock_settings, client: AsyncClient, valid_init_data: str
    ):
        """Invalid hash should return 401."""
        mock_settings.bot_token = TEST_BOT_TOKEN
        mock_settings.init_data_expire_seconds = 3600

        # Corrupt the hash
        corrupted = valid_init_data.replace("hash=", "hash=invalid")

        response = await client.get(
            "/api/me",
            headers={"Authorization": f"tma {corrupted}"},
        )

        assert response.status_code == 401
        assert "signature" in response.json()["detail"]

    @pytest.mark.asyncio
    @patch("services.auth.init_data.settings")
    async def test_expired_init_data_returns_401(
        self, mock_settings, client: AsyncClient, expired_init_data: str
    ):
        """Expired initData should return 401."""
        mock_settings.bot_token = TEST_BOT_TOKEN
        mock_settings.init_data_expire_seconds = 3600

        response = await client.get(
            "/api/me",
            headers={"Authorization": f"tma {expired_init_data}"},
        )

        assert response.status_code == 401
        assert "expired" in response.json()["detail"]

    @pytest.mark.asyncio
    @patch("services.auth.init_data.settings")
    async def test_creates_new_user(
        self, mock_settings, client: AsyncClient, valid_init_data: str
    ):
        """Should create new user on first auth."""
        mock_settings.bot_token = TEST_BOT_TOKEN
        mock_settings.init_data_expire_seconds = 3600

        # First request should create user
        response1 = await client.get(
            "/api/me",
            headers={"Authorization": f"tma {valid_init_data}"},
        )
        assert response1.status_code == 200
        user_id = response1.json()["user_id"]

        # Second request should return same user
        response2 = await client.get(
            "/api/me",
            headers={"Authorization": f"tma {valid_init_data}"},
        )
        assert response2.status_code == 200
        assert response2.json()["user_id"] == user_id

    @pytest.mark.asyncio
    async def test_malformed_init_data_returns_401(self, client: AsyncClient):
        """Malformed initData should return 401."""
        response = await client.get(
            "/api/me",
            headers={"Authorization": "tma not_valid_query_string"},
        )

        assert response.status_code == 401
