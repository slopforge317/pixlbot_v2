"""API tests for storage presign-upload endpoint."""

from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient


@pytest.fixture
def mock_storage_service() -> MagicMock:
    """Create a mock StorageService."""
    mock = MagicMock()
    mock.generate_presigned_put_url.return_value = (
        "https://test-bucket.account-id.r2.cloudflarestorage.com/signed-put-url",
        "uploads/1/550e8400-e29b-41d4-a716-446655440000.jpg",
    )
    return mock


class TestPresignUpload:
    """Tests for POST /api/storage/presign-upload."""

    @pytest.mark.asyncio
    async def test_presign_upload_success(
        self,
        auth_client: AsyncClient,
        mock_storage_service: MagicMock,
    ) -> None:
        """Test successful presign upload request."""
        with patch(
            "api.routes.storage.get_storage_service",
            return_value=mock_storage_service,
        ):
            response = await auth_client.post(
                "/api/storage/presign-upload",
                json={
                    "content_type": "image/jpeg",
                    "file_size": 1024,
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert "upload_url" in data
        assert "object_key" in data
        assert data["content_type"] == "image/jpeg"
        assert (
            data["object_key"] == "uploads/1/550e8400-e29b-41d4-a716-446655440000.jpg"
        )

    @pytest.mark.asyncio
    async def test_presign_upload_requires_auth(
        self,
        client: AsyncClient,
    ) -> None:
        """Test that presign upload requires authentication."""
        response = await client.post(
            "/api/storage/presign-upload",
            json={
                "content_type": "image/jpeg",
                "file_size": 1024,
            },
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_presign_upload_invalid_content_type(
        self,
        auth_client: AsyncClient,
        mock_storage_service: MagicMock,
    ) -> None:
        """Test rejection of unsupported content type."""
        mock_storage_service.generate_presigned_put_url.side_effect = ValueError(
            "Unsupported content type: image/gif"
        )

        with patch(
            "api.routes.storage.get_storage_service",
            return_value=mock_storage_service,
        ):
            response = await auth_client.post(
                "/api/storage/presign-upload",
                json={
                    "content_type": "image/gif",
                    "file_size": 1024,
                },
            )

        assert response.status_code == 400
        assert "Unsupported content type" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_presign_upload_file_too_large(
        self,
        auth_client: AsyncClient,
        mock_storage_service: MagicMock,
    ) -> None:
        """Test rejection of oversized file."""
        mock_storage_service.generate_presigned_put_url.side_effect = ValueError(
            "File size exceeds maximum of 10 MB"
        )

        with patch(
            "api.routes.storage.get_storage_service",
            return_value=mock_storage_service,
        ):
            response = await auth_client.post(
                "/api/storage/presign-upload",
                json={
                    "content_type": "image/jpeg",
                    "file_size": 20 * 1024 * 1024,
                },
            )

        assert response.status_code == 400
        assert "File size exceeds" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_presign_upload_invalid_file_size(
        self,
        auth_client: AsyncClient,
    ) -> None:
        """Test rejection of non-positive file size by Pydantic validation."""
        with patch(
            "api.routes.storage.get_storage_service",
            return_value=MagicMock(),
        ):
            response = await auth_client.post(
                "/api/storage/presign-upload",
                json={
                    "content_type": "image/jpeg",
                    "file_size": 0,
                },
            )

        assert response.status_code == 422  # Pydantic validation error

    @pytest.mark.asyncio
    async def test_presign_upload_storage_not_configured(
        self,
        auth_client: AsyncClient,
    ) -> None:
        """Test 503 when storage service is not configured."""
        with patch(
            "api.routes.storage.get_storage_service",
            side_effect=RuntimeError("Cloudflare R2 storage is not configured"),
        ):
            response = await auth_client.post(
                "/api/storage/presign-upload",
                json={
                    "content_type": "image/jpeg",
                    "file_size": 1024,
                },
            )

        assert response.status_code == 503
        assert "not configured" in response.json()["detail"]
