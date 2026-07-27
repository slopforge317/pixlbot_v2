"""Tests for Credit Packages API endpoints."""

from unittest.mock import patch

import pytest
from db.models import CreditPackage
from httpx import AsyncClient

from tests.test_api.conftest import TEST_BOT_TOKEN


class TestPackagesEndpoint:
    """Tests for /api/packages endpoint."""

    @pytest.mark.asyncio
    async def test_list_packages_unauthorized(self, client: AsyncClient) -> None:
        """Should return 401 without auth."""
        response = await client.get("/api/packages")
        assert response.status_code == 401

    @pytest.mark.asyncio
    @patch("services.auth.init_data.settings")
    async def test_list_packages(
        self,
        mock_settings,
        seed_packages: tuple[list[CreditPackage], AsyncClient],
        valid_init_data: str,
    ) -> None:
        """Should return list of active packages."""
        mock_settings.bot_token = TEST_BOT_TOKEN
        mock_settings.init_data_expire_seconds = 3600

        packages, client = seed_packages
        response = await client.get(
            "/api/packages",
            headers={"Authorization": f"tma {valid_init_data}"},
        )
        assert response.status_code == 200

        data = response.json()
        assert "packages" in data
        # Should have 3 active packages (inactive one filtered out)
        assert len(data["packages"]) == 3

        # Check package structure
        package = data["packages"][0]
        assert "id" in package
        assert "name" in package
        assert "description" in package
        assert "credit_amount" in package
        assert "price" in package
        assert "price_formatted" in package

    @pytest.mark.asyncio
    @patch("services.auth.init_data.settings")
    async def test_packages_sorted_by_price(
        self,
        mock_settings,
        seed_packages: tuple[list[CreditPackage], AsyncClient],
        valid_init_data: str,
    ) -> None:
        """Packages should be sorted by price ascending."""
        mock_settings.bot_token = TEST_BOT_TOKEN
        mock_settings.init_data_expire_seconds = 3600

        packages, client = seed_packages
        response = await client.get(
            "/api/packages",
            headers={"Authorization": f"tma {valid_init_data}"},
        )
        assert response.status_code == 200

        data = response.json()
        prices = [p["price"] for p in data["packages"]]
        assert prices == sorted(prices)
        assert prices == [9900, 24900, 69900]

    @pytest.mark.asyncio
    @patch("services.auth.init_data.settings")
    async def test_package_price_formatted(
        self,
        mock_settings,
        seed_packages: tuple[list[CreditPackage], AsyncClient],
        valid_init_data: str,
    ) -> None:
        """Package should have correctly formatted price."""
        mock_settings.bot_token = TEST_BOT_TOKEN
        mock_settings.init_data_expire_seconds = 3600

        packages, client = seed_packages
        response = await client.get(
            "/api/packages",
            headers={"Authorization": f"tma {valid_init_data}"},
        )
        assert response.status_code == 200

        data = response.json()
        package = data["packages"][0]
        assert package["price_formatted"] == "99.00 \u20bd"

    @pytest.mark.asyncio
    @patch("services.auth.init_data.settings")
    async def test_list_packages_empty(
        self,
        mock_settings,
        client: AsyncClient,
        valid_init_data: str,
    ) -> None:
        """Should return empty list if no active packages."""
        mock_settings.bot_token = TEST_BOT_TOKEN
        mock_settings.init_data_expire_seconds = 3600

        response = await client.get(
            "/api/packages",
            headers={"Authorization": f"tma {valid_init_data}"},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["packages"] == []
