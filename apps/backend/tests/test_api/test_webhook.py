"""Webhook endpoint tests."""

import os
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from api import create_app
from api.deps import get_db_session
from db.base import Base
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.db.models  # noqa: F401

# Test webhook secret
TEST_WEBHOOK_SECRET = "test_secret_token_12345"

# PostgreSQL test database URL
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://pixlbot:pixlbot_test@localhost:5432/pixlbot_pytest",
)


@pytest.fixture
async def webhook_client() -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client with webhook enabled."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    test_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Patch webhook settings for secret verification
    with patch("api.routes.webhook.settings") as mock_webhook_settings:
        mock_webhook_settings.webhook_secret = TEST_WEBHOOK_SECRET

        test_app = create_app()

        async def override_get_db_session() -> AsyncGenerator[AsyncSession, None]:
            async with test_session_maker() as session:
                try:
                    yield session
                    await session.commit()
                except Exception:
                    await session.rollback()
                    raise

        test_app.dependency_overrides[get_db_session] = override_get_db_session

        # Setup mock bot and dispatcher in app state
        mock_bot = MagicMock()
        mock_dispatcher = AsyncMock()
        mock_dispatcher.feed_update = AsyncMock()
        test_app.state.bot = mock_bot
        test_app.state.dispatcher = mock_dispatcher

        async with AsyncClient(
            transport=ASGITransport(app=test_app),
            base_url="http://test",
        ) as ac:
            # Store mocks for assertions
            ac._mock_bot = mock_bot  # type: ignore[attr-defined]
            ac._mock_dispatcher = mock_dispatcher  # type: ignore[attr-defined]
            yield ac

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


class TestWebhookEndpoint:
    """Tests for POST /webhook/telegram endpoint."""

    async def test_webhook_valid_update(self, webhook_client: AsyncClient) -> None:
        """Valid update with correct secret should be processed."""
        update_data = {
            "update_id": 123456789,
            "message": {
                "message_id": 1,
                "from": {"id": 123, "is_bot": False, "first_name": "Test"},
                "chat": {"id": 123, "type": "private"},
                "date": 1234567890,
                "text": "/start",
            },
        }

        response = await webhook_client.post(
            "/webhook/telegram",
            json=update_data,
            headers={"X-Telegram-Bot-Api-Secret-Token": TEST_WEBHOOK_SECRET},
        )

        assert response.status_code == 200
        assert response.json() == {"ok": True}

        # Verify dispatcher was called
        dispatcher = webhook_client._mock_dispatcher  # type: ignore[attr-defined]
        dispatcher.feed_update.assert_called_once()

    async def test_webhook_invalid_secret(self, webhook_client: AsyncClient) -> None:
        """Request with invalid secret token should return 403."""
        update_data = {"update_id": 123}

        response = await webhook_client.post(
            "/webhook/telegram",
            json=update_data,
            headers={"X-Telegram-Bot-Api-Secret-Token": "wrong_secret"},
        )

        assert response.status_code == 403
        assert response.json()["detail"] == "Invalid secret token"

    async def test_webhook_missing_secret(self, webhook_client: AsyncClient) -> None:
        """Request without secret token should return 403."""
        update_data = {"update_id": 123}

        response = await webhook_client.post(
            "/webhook/telegram",
            json=update_data,
        )

        assert response.status_code == 403
        assert response.json()["detail"] == "Invalid secret token"

    async def test_webhook_callback_query_update(
        self, webhook_client: AsyncClient
    ) -> None:
        """Callback query update should be processed."""
        update_data = {
            "update_id": 123456790,
            "callback_query": {
                "id": "123",
                "from": {"id": 123, "is_bot": False, "first_name": "Test"},
                "chat_instance": "123",
                "data": "button_click",
            },
        }

        response = await webhook_client.post(
            "/webhook/telegram",
            json=update_data,
            headers={"X-Telegram-Bot-Api-Secret-Token": TEST_WEBHOOK_SECRET},
        )

        assert response.status_code == 200
        assert response.json() == {"ok": True}

    async def test_webhook_returns_ok_on_processing_error(
        self, webhook_client: AsyncClient
    ) -> None:
        """Even if processing fails, webhook should return 200 to prevent retries."""
        # Make dispatcher raise an exception
        dispatcher = webhook_client._mock_dispatcher  # type: ignore[attr-defined]
        dispatcher.feed_update.side_effect = Exception("Processing error")

        update_data = {
            "update_id": 123456789,
            "message": {
                "message_id": 1,
                "from": {"id": 123, "is_bot": False, "first_name": "Test"},
                "chat": {"id": 123, "type": "private"},
                "date": 1234567890,
                "text": "/start",
            },
        }

        response = await webhook_client.post(
            "/webhook/telegram",
            json=update_data,
            headers={"X-Telegram-Bot-Api-Secret-Token": TEST_WEBHOOK_SECRET},
        )

        # Should still return 200 to prevent Telegram from retrying
        assert response.status_code == 200
        assert response.json() == {"ok": True}


class TestWebhookAlwaysRegistered:
    """Test that webhook endpoint is always available (for YooKassa etc)."""

    async def test_webhook_available_without_webhook_enabled(self) -> None:
        """Webhook endpoint is registered even when webhook_enabled=False."""
        engine = create_async_engine(TEST_DATABASE_URL, echo=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        test_session_maker = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )

        test_app = create_app()

        async def override_get_db_session() -> AsyncGenerator[AsyncSession, None]:
            async with test_session_maker() as session:
                try:
                    yield session
                    await session.commit()
                except Exception:
                    await session.rollback()
                    raise

        test_app.dependency_overrides[get_db_session] = override_get_db_session

        # Setup mock bot and dispatcher
        test_app.state.bot = MagicMock()
        test_app.state.dispatcher = AsyncMock()

        async with AsyncClient(
            transport=ASGITransport(app=test_app),
            base_url="http://test",
        ) as ac:
            response = await ac.post(
                "/webhook/telegram",
                json={"update_id": 123},
                headers={"X-Telegram-Bot-Api-Secret-Token": "any"},
            )

            # Should be 403 (invalid secret), not 404
            assert response.status_code == 403

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

        await engine.dispose()
