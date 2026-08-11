"""Tests for Providers API endpoints."""

from unittest.mock import patch

import pytest
from db.models import Provider
from httpx import AsyncClient

from tests.test_api.conftest import TEST_BOT_TOKEN


class TestProvidersEndpoint:
    """Tests for /api/providers endpoint."""

    @pytest.mark.asyncio
    async def test_list_providers_unauthorized(self, client: AsyncClient) -> None:
        """Should return 401 without auth."""
        response = await client.get("/api/providers")
        assert response.status_code == 401

    @pytest.mark.asyncio
    @patch("services.auth.init_data.settings")
    async def test_list_providers(
        self,
        mock_settings,
        seed_models: tuple[list[Provider], AsyncClient],
        valid_init_data: str,
    ) -> None:
        """Should return list of providers with models and pricing."""
        mock_settings.bot_token = TEST_BOT_TOKEN
        mock_settings.init_data_expire_seconds = 3600

        providers, client = seed_models
        response = await client.get(
            "/api/providers",
            headers={"Authorization": f"tma {valid_init_data}"},
        )
        assert response.status_code == 200

        data = response.json()
        assert "providers" in data
        assert len(data["providers"]) == 2  # image + video providers

        # Check first provider structure
        provider = data["providers"][0]
        assert "id" in provider
        assert provider["slug"] == "test-image-provider"
        assert "title" in provider
        assert "gen_type" in provider
        assert "sort_order" in provider
        assert "models" in provider
        assert len(provider["models"]) > 0

        # Check model structure
        model = provider["models"][0]
        assert "id" in model
        assert "api_model_id" in model
        assert "title" in model
        assert model["input_mode"] == "text_only"
        assert "sort_order" in model
        assert "input_schema" in model
        assert "variant_keys" in model
        assert "pricing" in model

        # Check pricing structure
        assert len(model["pricing"]) > 0
        pricing = model["pricing"][0]
        assert "id" in pricing
        assert "variant_values" in pricing
        assert "price" in pricing

    @pytest.mark.asyncio
    @patch("services.auth.init_data.settings")
    async def test_list_providers_filter_by_image(
        self,
        mock_settings,
        seed_models: tuple[list[Provider], AsyncClient],
        valid_init_data: str,
    ) -> None:
        """Should filter providers by image gen_type."""
        mock_settings.bot_token = TEST_BOT_TOKEN
        mock_settings.init_data_expire_seconds = 3600

        providers, client = seed_models
        response = await client.get(
            "/api/providers?gen_type=image",
            headers={"Authorization": f"tma {valid_init_data}"},
        )
        assert response.status_code == 200

        data = response.json()
        assert len(data["providers"]) == 1
        assert data["providers"][0]["gen_type"] == "image"
        assert data["providers"][0]["title"] == "Test Image Provider"

    @pytest.mark.asyncio
    @patch("services.auth.init_data.settings")
    async def test_list_providers_filter_by_video(
        self,
        mock_settings,
        seed_models: tuple[list[Provider], AsyncClient],
        valid_init_data: str,
    ) -> None:
        """Should filter providers by video gen_type."""
        mock_settings.bot_token = TEST_BOT_TOKEN
        mock_settings.init_data_expire_seconds = 3600

        providers, client = seed_models
        response = await client.get(
            "/api/providers?gen_type=video",
            headers={"Authorization": f"tma {valid_init_data}"},
        )
        assert response.status_code == 200

        data = response.json()
        assert len(data["providers"]) == 1
        assert data["providers"][0]["gen_type"] == "video"
        assert data["providers"][0]["title"] == "Test Video Provider"

    @pytest.mark.asyncio
    @patch("services.auth.init_data.settings")
    async def test_list_providers_empty(
        self,
        mock_settings,
        client: AsyncClient,
        valid_init_data: str,
    ) -> None:
        """Should return empty list if no providers."""
        mock_settings.bot_token = TEST_BOT_TOKEN
        mock_settings.init_data_expire_seconds = 3600

        response = await client.get(
            "/api/providers",
            headers={"Authorization": f"tma {valid_init_data}"},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["providers"] == []

    @pytest.mark.asyncio
    @patch("services.auth.init_data.settings")
    async def test_list_providers_excludes_inactive_pricing(
        self,
        mock_settings,
        seed_models: tuple[list[Provider], AsyncClient],
        valid_init_data: str,
    ) -> None:
        """Should exclude inactive pricing variants."""
        mock_settings.bot_token = TEST_BOT_TOKEN
        mock_settings.init_data_expire_seconds = 3600

        providers, client = seed_models
        response = await client.get(
            "/api/providers?gen_type=image",
            headers={"Authorization": f"tma {valid_init_data}"},
        )
        assert response.status_code == 200

        data = response.json()
        image_provider = data["providers"][0]
        image_model = image_provider["models"][0]
        # Should have 2 active pricing variants (not 3 - inactive excluded)
        assert len(image_model["pricing"]) == 2
