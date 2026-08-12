"""Integration tests for generations API."""

from datetime import datetime
from unittest.mock import patch

import pytest
from db.enums import JobStatus, TransactionType
from db.models import (
    AIModel,
    GenerationJob,
    PricingVariant,
    Provider,
    Transaction,
    User,
)
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.test_api.conftest import TEST_BOT_TOKEN, generate_init_data


class TestCreateGeneration:
    """Tests for POST /api/generations endpoint."""

    @pytest.mark.asyncio
    @patch("api.routes.generations.process_generation")
    @patch("services.auth.init_data.settings")
    async def test_create_generation_success(
        self,
        mock_settings,
        mock_process_generation,
        db_session_and_client: tuple[AsyncSession, AsyncClient],
    ):
        """Create generation with sufficient balance."""
        mock_settings.bot_token = TEST_BOT_TOKEN
        mock_settings.init_data_expire_seconds = 3600

        session, client = db_session_and_client

        # Create user
        user = User(
            telegram_user_id=123456789,
            chat_id=123456789,
            first_name="Test",
        )
        session.add(user)
        await session.flush()

        # Create provider, model and pricing variant
        provider = Provider(title="TestProvider", gen_type="image", active=True)
        session.add(provider)
        await session.flush()

        model = AIModel(
            provider_id=provider.id,
            api_model_id="test/text-to-image",
            title="Text-to-Image",
            input_schema={"prompt": {"type": "string"}},
            variant_keys=[],
            active=True,
        )
        session.add(model)
        await session.flush()

        pv = PricingVariant(
            model_id=model.id,
            variant_values={},
            price=10,
            active=True,
        )
        session.add(pv)
        await session.flush()

        # Add credits to user
        deposit = Transaction(
            user_id=user.user_id,
            type=TransactionType.deposit,
            amount_credits=100,
        )
        session.add(deposit)
        await session.commit()

        # Create generation
        init_data = generate_init_data(TEST_BOT_TOKEN)
        response = await client.post(
            "/api/generations",
            json={
                "model": {
                    "id": model.id,
                    "api_model_id": "test/text-to-image",
                    "title": "Text-to-Image",
                },
                "variant": {
                    "id": pv.id,
                    "price": 10,
                    "variant_values": {},
                },
                "input": {
                    "prompt": "A beautiful sunset",
                    "seed": 12345,
                },
            },
            headers={"Authorization": f"tma {init_data}"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "queue"
        assert data["pricing_variant_id"] == pv.id
        assert data["cost_credit"] == 10
        assert data["prompt"] == "A beautiful sunset"
        assert "job_id" in data
        assert "created_at" in data

    @pytest.mark.asyncio
    @patch("services.auth.init_data.settings")
    async def test_create_generation_insufficient_credits(
        self,
        mock_settings,
        db_session_and_client: tuple[AsyncSession, AsyncClient],
    ):
        """Create generation with insufficient balance returns 400."""
        mock_settings.bot_token = TEST_BOT_TOKEN
        mock_settings.init_data_expire_seconds = 3600

        session, client = db_session_and_client

        # Create user with low balance
        user = User(
            telegram_user_id=123456789,
            chat_id=123456789,
            first_name="Test",
        )
        session.add(user)
        await session.flush()

        # Create provider, model and pricing variant
        provider = Provider(title="TestProvider", gen_type="image", active=True)
        session.add(provider)
        await session.flush()

        model = AIModel(
            provider_id=provider.id,
            api_model_id="test/text-to-image",
            title="Text-to-Image",
            input_schema={},
            variant_keys=[],
            active=True,
        )
        session.add(model)
        await session.flush()

        pv = PricingVariant(
            model_id=model.id,
            variant_values={},
            price=100,
            active=True,
        )
        session.add(pv)
        await session.flush()

        # Add only 5 credits
        deposit = Transaction(
            user_id=user.user_id,
            type=TransactionType.deposit,
            amount_credits=5,
        )
        session.add(deposit)
        await session.commit()

        init_data = generate_init_data(TEST_BOT_TOKEN)
        response = await client.post(
            "/api/generations",
            json={
                "model": {
                    "id": model.id,
                    "api_model_id": "test/text-to-image",
                    "title": "Text-to-Image",
                },
                "variant": {
                    "id": pv.id,
                    "price": 100,
                    "variant_values": {},
                },
                "input": {"prompt": "Test prompt"},
            },
            headers={"Authorization": f"tma {init_data}"},
        )

        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["detail"] == "Insufficient credits"
        assert data["detail"]["balance"] == 5
        assert data["detail"]["required"] == 100

    @pytest.mark.asyncio
    @patch("services.auth.init_data.settings")
    async def test_create_generation_variant_not_found(
        self,
        mock_settings,
        db_session_and_client: tuple[AsyncSession, AsyncClient],
    ):
        """Create generation with non-existent pricing variant returns 404."""
        mock_settings.bot_token = TEST_BOT_TOKEN
        mock_settings.init_data_expire_seconds = 3600

        session, client = db_session_and_client

        # Create user
        user = User(
            telegram_user_id=123456789,
            chat_id=123456789,
            first_name="Test",
        )
        session.add(user)
        await session.commit()

        init_data = generate_init_data(TEST_BOT_TOKEN)
        response = await client.post(
            "/api/generations",
            json={
                "model": {
                    "id": 1,
                    "api_model_id": "test/model",
                    "title": "Test",
                },
                "variant": {
                    "id": 99999,
                    "price": 10,
                    "variant_values": {},
                },
                "input": {"prompt": "Test prompt"},
            },
            headers={"Authorization": f"tma {init_data}"},
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    @patch("services.auth.init_data.settings")
    async def test_create_generation_inactive_variant(
        self,
        mock_settings,
        db_session_and_client: tuple[AsyncSession, AsyncClient],
    ):
        """Create generation with inactive pricing variant returns 404."""
        mock_settings.bot_token = TEST_BOT_TOKEN
        mock_settings.init_data_expire_seconds = 3600

        session, client = db_session_and_client

        # Create user
        user = User(
            telegram_user_id=123456789,
            chat_id=123456789,
            first_name="Test",
        )
        session.add(user)
        await session.flush()

        # Create provider, model and inactive pricing variant
        provider = Provider(title="TestProvider", gen_type="image", active=True)
        session.add(provider)
        await session.flush()

        model = AIModel(
            provider_id=provider.id,
            api_model_id="test/text-to-image",
            title="Text-to-Image",
            input_schema={},
            variant_keys=[],
            active=True,
        )
        session.add(model)
        await session.flush()

        pv = PricingVariant(
            model_id=model.id,
            variant_values={},
            price=10,
            active=False,
        )
        session.add(pv)
        await session.commit()

        init_data = generate_init_data(TEST_BOT_TOKEN)
        response = await client.post(
            "/api/generations",
            json={
                "model": {
                    "id": model.id,
                    "api_model_id": "test/text-to-image",
                    "title": "Text-to-Image",
                },
                "variant": {
                    "id": pv.id,
                    "price": 10,
                    "variant_values": {},
                },
                "input": {"prompt": "Test prompt"},
            },
            headers={"Authorization": f"tma {init_data}"},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    @patch("services.auth.init_data.settings")
    async def test_create_generation_price_mismatch(
        self,
        mock_settings,
        db_session_and_client: tuple[AsyncSession, AsyncClient],
    ):
        """Create generation with stale price returns 409."""
        mock_settings.bot_token = TEST_BOT_TOKEN
        mock_settings.init_data_expire_seconds = 3600

        session, client = db_session_and_client

        # Create user
        user = User(
            telegram_user_id=123456789,
            chat_id=123456789,
            first_name="Test",
        )
        session.add(user)
        await session.flush()

        # Create provider, model and pricing variant
        provider = Provider(title="TestProvider", gen_type="image", active=True)
        session.add(provider)
        await session.flush()

        model = AIModel(
            provider_id=provider.id,
            api_model_id="test/text-to-image",
            title="Text-to-Image",
            input_schema={},
            variant_keys=[],
            active=True,
        )
        session.add(model)
        await session.flush()

        pv = PricingVariant(
            model_id=model.id,
            variant_values={},
            price=15,  # DB price is 15
            active=True,
        )
        session.add(pv)
        await session.flush()

        # Add credits
        deposit = Transaction(
            user_id=user.user_id,
            type=TransactionType.deposit,
            amount_credits=100,
        )
        session.add(deposit)
        await session.commit()

        init_data = generate_init_data(TEST_BOT_TOKEN)
        response = await client.post(
            "/api/generations",
            json={
                "model": {
                    "id": model.id,
                    "api_model_id": "test/text-to-image",
                    "title": "Text-to-Image",
                },
                "variant": {
                    "id": pv.id,
                    "price": 10,  # Client sends stale price 10
                    "variant_values": {},
                },
                "input": {"prompt": "Test prompt"},
            },
            headers={"Authorization": f"tma {init_data}"},
        )

        assert response.status_code == 409
        assert "price has changed" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_create_generation_unauthorized(
        self, db_session_and_client: tuple[AsyncSession, AsyncClient]
    ):
        """Create generation without auth returns 401."""
        _, client = db_session_and_client

        response = await client.post(
            "/api/generations",
            json={
                "model": {
                    "id": 1,
                    "api_model_id": "test/model",
                    "title": "Test",
                },
                "variant": {
                    "id": 1,
                    "price": 10,
                    "variant_values": {},
                },
                "input": {"prompt": "Test prompt"},
            },
        )

        assert response.status_code == 401


class TestListGenerations:
    """Tests for GET /api/generations endpoint."""

    @pytest.mark.asyncio
    @patch("services.auth.init_data.settings")
    async def test_list_generations_success(
        self,
        mock_settings,
        db_session_and_client: tuple[AsyncSession, AsyncClient],
    ):
        """List user's generations with pagination."""
        mock_settings.bot_token = TEST_BOT_TOKEN
        mock_settings.init_data_expire_seconds = 3600

        session, client = db_session_and_client

        # Create user
        user = User(
            telegram_user_id=123456789,
            chat_id=123456789,
            first_name="Test",
        )
        session.add(user)
        await session.flush()

        # Create provider, model and pricing variant
        provider = Provider(title="TestProvider", gen_type="image", active=True)
        session.add(provider)
        await session.flush()

        model = AIModel(
            provider_id=provider.id,
            api_model_id="test/text-to-image",
            title="Text-to-Image",
            input_schema={},
            variant_keys=[],
            active=True,
        )
        session.add(model)
        await session.flush()

        pv = PricingVariant(
            model_id=model.id,
            variant_values={},
            price=10,
            active=True,
        )
        session.add(pv)
        await session.flush()

        # Create some generation jobs
        for i in range(3):
            job = GenerationJob(
                user_id=user.user_id,
                pricing_variant_id=pv.id,
                status=JobStatus.done if i < 2 else JobStatus.error,
                cost_credit=10,
                prompt=f"Test prompt {i}",
                generation_params={"prompt": f"Test prompt {i}"},
                error="Generation failed" if i == 2 else None,
                provider_complete_time=(
                    datetime(2026, 7, 9, 10, 1) if i == 0 else None
                ),
            )
            session.add(job)
        await session.commit()

        init_data = generate_init_data(TEST_BOT_TOKEN)
        response = await client.get(
            "/api/generations",
            headers={"Authorization": f"tma {init_data}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["generations"]) == 3
        assert data["limit"] == 10
        assert data["offset"] == 0
        assert data["generations"][0]["created_at"].endswith("Z")
        failed_generation = next(
            item for item in data["generations"] if item["status"] == "error"
        )
        assert failed_generation["error_message"] == "Generation failed"
        assert failed_generation["completed_at"] is None
        completed_generation = next(
            item for item in data["generations"] if item["completed_at"] is not None
        )
        assert completed_generation["completed_at"] == "2026-07-09T10:01:00Z"

    @pytest.mark.asyncio
    @patch("services.auth.init_data.settings")
    async def test_list_generations_with_status_filter(
        self,
        mock_settings,
        db_session_and_client: tuple[AsyncSession, AsyncClient],
    ):
        """List generations filtered by status."""
        mock_settings.bot_token = TEST_BOT_TOKEN
        mock_settings.init_data_expire_seconds = 3600

        session, client = db_session_and_client

        # Create user
        user = User(
            telegram_user_id=123456789,
            chat_id=123456789,
            first_name="Test",
        )
        session.add(user)
        await session.flush()

        # Create provider, model and pricing variant
        provider = Provider(title="TestProvider", gen_type="image", active=True)
        session.add(provider)
        await session.flush()

        model = AIModel(
            provider_id=provider.id,
            api_model_id="test/text-to-image",
            title="Text-to-Image",
            input_schema={},
            variant_keys=[],
            active=True,
        )
        session.add(model)
        await session.flush()

        pv = PricingVariant(
            model_id=model.id,
            variant_values={},
            price=10,
            active=True,
        )
        session.add(pv)
        await session.flush()

        # Create jobs with different statuses
        job_done = GenerationJob(
            user_id=user.user_id,
            pricing_variant_id=pv.id,
            status=JobStatus.done,
            cost_credit=10,
            prompt="Done job",
            generation_params={"prompt": "Done job"},
        )
        job_queue = GenerationJob(
            user_id=user.user_id,
            pricing_variant_id=pv.id,
            status=JobStatus.queue,
            cost_credit=10,
            prompt="Queue job",
            generation_params={"prompt": "Queue job"},
        )
        session.add_all([job_done, job_queue])
        await session.commit()

        init_data = generate_init_data(TEST_BOT_TOKEN)
        response = await client.get(
            "/api/generations?status=done",
            headers={"Authorization": f"tma {init_data}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["generations"]) == 1
        assert data["generations"][0]["status"] == "done"

    @pytest.mark.asyncio
    @patch("services.auth.init_data.settings")
    async def test_list_generations_pagination(
        self,
        mock_settings,
        db_session_and_client: tuple[AsyncSession, AsyncClient],
    ):
        """List generations with pagination params."""
        mock_settings.bot_token = TEST_BOT_TOKEN
        mock_settings.init_data_expire_seconds = 3600

        session, client = db_session_and_client

        # Create user
        user = User(
            telegram_user_id=123456789,
            chat_id=123456789,
            first_name="Test",
        )
        session.add(user)
        await session.flush()

        # Create provider, model and pricing variant
        provider = Provider(title="TestProvider", gen_type="image", active=True)
        session.add(provider)
        await session.flush()

        model = AIModel(
            provider_id=provider.id,
            api_model_id="test/text-to-image",
            title="Text-to-Image",
            input_schema={},
            variant_keys=[],
            active=True,
        )
        session.add(model)
        await session.flush()

        pv = PricingVariant(
            model_id=model.id,
            variant_values={},
            price=10,
            active=True,
        )
        session.add(pv)
        await session.flush()

        # Create 5 jobs
        for i in range(5):
            job = GenerationJob(
                user_id=user.user_id,
                pricing_variant_id=pv.id,
                status=JobStatus.done,
                cost_credit=10,
                prompt=f"Test prompt {i}",
                generation_params={"prompt": f"Test prompt {i}"},
            )
            session.add(job)
        await session.commit()

        init_data = generate_init_data(TEST_BOT_TOKEN)
        response = await client.get(
            "/api/generations?limit=2&offset=1",
            headers={"Authorization": f"tma {init_data}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["generations"]) == 2
        assert data["limit"] == 2
        assert data["offset"] == 1

    @pytest.mark.asyncio
    async def test_list_generations_unauthorized(
        self, db_session_and_client: tuple[AsyncSession, AsyncClient]
    ):
        """List generations without auth returns 401."""
        _, client = db_session_and_client

        response = await client.get("/api/generations")
        assert response.status_code == 401


class TestGetGeneration:
    """Tests for GET /api/generations/{job_id} endpoint."""

    @pytest.mark.asyncio
    @patch("services.auth.init_data.settings")
    async def test_get_generation_success(
        self,
        mock_settings,
        db_session_and_client: tuple[AsyncSession, AsyncClient],
    ):
        """Get specific generation details."""
        mock_settings.bot_token = TEST_BOT_TOKEN
        mock_settings.init_data_expire_seconds = 3600

        session, client = db_session_and_client

        # Create user
        user = User(
            telegram_user_id=123456789,
            chat_id=123456789,
            first_name="Test",
        )
        session.add(user)
        await session.flush()

        # Create provider, model and pricing variant
        provider = Provider(title="TestProvider", gen_type="image", active=True)
        session.add(provider)
        await session.flush()

        model = AIModel(
            provider_id=provider.id,
            api_model_id="test/text-to-image",
            title="Text-to-Image",
            input_schema={},
            variant_keys=[],
            active=True,
        )
        session.add(model)
        await session.flush()

        pv = PricingVariant(
            model_id=model.id,
            variant_values={},
            price=10,
            active=True,
        )
        session.add(pv)
        await session.flush()

        # Create job
        job = GenerationJob(
            user_id=user.user_id,
            pricing_variant_id=pv.id,
            status=JobStatus.done,
            cost_credit=10,
            prompt="Test prompt",
            generation_params={"prompt": "Test prompt", "seed": 123},
            success_url_asset="https://example.com/image.png",
        )
        session.add(job)
        await session.commit()

        init_data = generate_init_data(TEST_BOT_TOKEN)
        response = await client.get(
            f"/api/generations/{job.job_id}",
            headers={"Authorization": f"tma {init_data}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == job.job_id
        assert data["status"] == "done"
        assert data["prompt"] == "Test prompt"
        assert data["model_title"] == "Text-to-Image"
        assert data["provider_title"] == "TestProvider"
        assert data["params"]["seed"] == 123
        assert data["result_url"] == "https://example.com/image.png"

    @pytest.mark.asyncio
    @patch("services.auth.init_data.settings")
    async def test_get_generation_not_found(
        self,
        mock_settings,
        db_session_and_client: tuple[AsyncSession, AsyncClient],
    ):
        """Get non-existent generation returns 404."""
        mock_settings.bot_token = TEST_BOT_TOKEN
        mock_settings.init_data_expire_seconds = 3600

        session, client = db_session_and_client

        # Create user
        user = User(
            telegram_user_id=123456789,
            chat_id=123456789,
            first_name="Test",
        )
        session.add(user)
        await session.commit()

        init_data = generate_init_data(TEST_BOT_TOKEN)
        response = await client.get(
            "/api/generations/99999",
            headers={"Authorization": f"tma {init_data}"},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    @patch("services.auth.init_data.settings")
    async def test_get_generation_other_user(
        self,
        mock_settings,
        db_session_and_client: tuple[AsyncSession, AsyncClient],
    ):
        """Get another user's generation returns 404."""
        mock_settings.bot_token = TEST_BOT_TOKEN
        mock_settings.init_data_expire_seconds = 3600

        session, client = db_session_and_client

        # Create two users
        user1 = User(
            telegram_user_id=111111111,
            chat_id=111111111,
            first_name="User1",
        )
        user2 = User(
            telegram_user_id=123456789,  # This matches init_data user
            chat_id=123456789,
            first_name="User2",
        )
        session.add_all([user1, user2])
        await session.flush()

        # Create provider, model and pricing variant
        provider = Provider(title="TestProvider", gen_type="image", active=True)
        session.add(provider)
        await session.flush()

        model = AIModel(
            provider_id=provider.id,
            api_model_id="test/text-to-image",
            title="Text-to-Image",
            input_schema={},
            variant_keys=[],
            active=True,
        )
        session.add(model)
        await session.flush()

        pv = PricingVariant(
            model_id=model.id,
            variant_values={},
            price=10,
            active=True,
        )
        session.add(pv)
        await session.flush()

        # Create job for user1 (not the authenticated user)
        job = GenerationJob(
            user_id=user1.user_id,
            pricing_variant_id=pv.id,
            status=JobStatus.done,
            cost_credit=10,
            prompt="Secret prompt",
            generation_params={"prompt": "Secret prompt"},
        )
        session.add(job)
        await session.commit()

        # Try to access user1's job as user2
        init_data = generate_init_data(TEST_BOT_TOKEN)  # user_id=123456789 (user2)
        response = await client.get(
            f"/api/generations/{job.job_id}",
            headers={"Authorization": f"tma {init_data}"},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_generation_unauthorized(
        self, db_session_and_client: tuple[AsyncSession, AsyncClient]
    ):
        """Get generation without auth returns 401."""
        _, client = db_session_and_client

        response = await client.get("/api/generations/1")
        assert response.status_code == 401
