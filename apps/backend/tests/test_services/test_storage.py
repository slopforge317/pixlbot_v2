"""Tests for StorageService."""

from unittest.mock import MagicMock, patch

import pytest
from services.storage import service as storage_module
from services.storage.service import (
    StorageService,
    get_storage_service,
    is_valid_object_key,
)


@pytest.fixture
def storage_service() -> StorageService:
    """Create a Cloudflare R2 StorageService with mocked boto3 client."""
    with patch("services.storage.service.boto3") as mock_boto3:
        mock_client = MagicMock()
        mock_client.generate_presigned_url.return_value = (
            "https://test-bucket.account-id.r2.cloudflarestorage.com/signed-url"
        )
        mock_boto3.client.return_value = mock_client

        service = StorageService(
            access_key_id="test_key",
            secret_access_key="test_secret",
            bucket_name="test-bucket",
            endpoint_url="https://account-id.r2.cloudflarestorage.com",
            region="auto",
            upload_max_size_bytes=10 * 1024 * 1024,
            presign_upload_expires=600,
            presign_download_expires=3600,
        )
        # Store mock for assertions
        service._mock_client = mock_client  # type: ignore[attr-defined]
        return service


class TestObjectKeyPattern:
    """Tests for OBJECT_KEY_PATTERN regex."""

    def test_valid_keys(self) -> None:
        """Test valid object key patterns."""
        valid_keys = [
            "uploads/1/550e8400-e29b-41d4-a716-446655440000.jpg",
            "uploads/42/a1b2c3d4-e5f6-7890-abcd-ef1234567890.png",
            "uploads/999999/00000000-0000-0000-0000-000000000000.webp",
        ]
        for key in valid_keys:
            assert is_valid_object_key(key), f"Should be valid: {key}"

    def test_invalid_keys(self) -> None:
        """Test invalid object key patterns (path traversal, etc)."""
        invalid_keys = [
            "",
            "uploads/../etc/passwd",
            "uploads/1/../../secret.jpg",
            # non-numeric user_id
            "uploads/abc/550e8400-e29b-41d4-a716-446655440000.jpg",
            "uploads/1/not-a-uuid.jpg",
            # wrong extension
            "uploads/1/550e8400-e29b-41d4-a716-446655440000.gif",
            "uploads/1/550e8400-e29b-41d4-a716-446655440000.jpg/extra",
            # wrong prefix
            "other/1/550e8400-e29b-41d4-a716-446655440000.jpg",
            # base64 data URI
            "data:image/jpeg;base64,/9j/4AAQ...",
        ]
        for key in invalid_keys:
            assert not is_valid_object_key(key), f"Should be invalid: {key}"


class TestGetStorageService:
    """Tests for Cloudflare R2 configuration validation."""

    def test_requires_every_credential(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(storage_module, "_storage_service", None)
        monkeypatch.setattr(storage_module.settings, "r2_access_key_id", "access")
        monkeypatch.setattr(storage_module.settings, "r2_secret_access_key", "")
        monkeypatch.setattr(storage_module.settings, "r2_bucket_name", "bucket")
        monkeypatch.setattr(
            storage_module.settings,
            "r2_endpoint_url",
            "https://account-id.r2.cloudflarestorage.com",
        )

        with pytest.raises(RuntimeError, match="R2_SECRET_ACCESS_KEY"):
            get_storage_service()

    def test_builds_client_from_r2_settings(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(storage_module, "_storage_service", None)
        monkeypatch.setattr(storage_module.settings, "r2_access_key_id", "access")
        monkeypatch.setattr(storage_module.settings, "r2_secret_access_key", "secret")
        monkeypatch.setattr(storage_module.settings, "r2_bucket_name", "bucket")
        monkeypatch.setattr(
            storage_module.settings,
            "r2_endpoint_url",
            "https://account-id.r2.cloudflarestorage.com/",
        )
        monkeypatch.setattr(storage_module.settings, "r2_region", "auto")

        with patch("services.storage.service.boto3.client") as mock_client_factory:
            service = get_storage_service()

        assert isinstance(service, StorageService)
        call_kwargs = mock_client_factory.call_args.kwargs
        assert call_kwargs["endpoint_url"] == (
            "https://account-id.r2.cloudflarestorage.com"
        )
        assert call_kwargs["region_name"] == "auto"
        assert call_kwargs["aws_access_key_id"] == "access"
        assert call_kwargs["aws_secret_access_key"] == "secret"


class TestGeneratePresignedPutUrl:
    """Tests for generate_presigned_put_url."""

    def test_valid_jpeg_upload(self, storage_service: StorageService) -> None:
        """Test presigned PUT URL generation for JPEG."""
        put_url, object_key = storage_service.generate_presigned_put_url(
            user_id=42,
            content_type="image/jpeg",
            file_size=1024,
        )

        assert put_url.startswith("https://")
        assert object_key.startswith("uploads/42/")
        assert object_key.endswith(".jpg")
        assert is_valid_object_key(object_key)

    def test_valid_png_upload(self, storage_service: StorageService) -> None:
        """Test presigned PUT URL generation for PNG."""
        _, object_key = storage_service.generate_presigned_put_url(
            user_id=1,
            content_type="image/png",
            file_size=5000,
        )

        assert object_key.endswith(".png")
        assert is_valid_object_key(object_key)

    def test_valid_webp_upload(self, storage_service: StorageService) -> None:
        """Test presigned PUT URL generation for WebP."""
        _, object_key = storage_service.generate_presigned_put_url(
            user_id=1,
            content_type="image/webp",
            file_size=5000,
        )

        assert object_key.endswith(".webp")
        assert is_valid_object_key(object_key)

    def test_unsupported_content_type(self, storage_service: StorageService) -> None:
        """Test rejection of unsupported content type."""
        with pytest.raises(ValueError, match="Unsupported content type"):
            storage_service.generate_presigned_put_url(
                user_id=1,
                content_type="image/gif",
                file_size=1024,
            )

    def test_zero_file_size(self, storage_service: StorageService) -> None:
        """Test rejection of zero file size."""
        with pytest.raises(ValueError, match="File size must be positive"):
            storage_service.generate_presigned_put_url(
                user_id=1,
                content_type="image/jpeg",
                file_size=0,
            )

    def test_negative_file_size(self, storage_service: StorageService) -> None:
        """Test rejection of negative file size."""
        with pytest.raises(ValueError, match="File size must be positive"):
            storage_service.generate_presigned_put_url(
                user_id=1,
                content_type="image/jpeg",
                file_size=-100,
            )

    def test_file_too_large(self, storage_service: StorageService) -> None:
        """Test rejection of file exceeding max size."""
        with pytest.raises(ValueError, match="File size exceeds maximum"):
            storage_service.generate_presigned_put_url(
                user_id=1,
                content_type="image/jpeg",
                file_size=20 * 1024 * 1024,  # 20 MB > 10 MB limit
            )

    def test_boto3_called_with_correct_params(
        self, storage_service: StorageService
    ) -> None:
        """Test that boto3 is called with correct parameters."""
        storage_service.generate_presigned_put_url(
            user_id=42,
            content_type="image/jpeg",
            file_size=1024,
        )

        mock_client = storage_service._mock_client  # type: ignore[attr-defined]
        mock_client.generate_presigned_url.assert_called_once()
        call_args = mock_client.generate_presigned_url.call_args

        assert call_args[0][0] == "put_object"
        params = call_args[1]["Params"]
        assert params["Bucket"] == "test-bucket"
        assert params["Key"].startswith("uploads/42/")
        assert params["ContentType"] == "image/jpeg"
        assert call_args[1]["ExpiresIn"] == 600

    def test_unique_keys_per_call(self, storage_service: StorageService) -> None:
        """Test that each call generates a unique object key."""
        _, key1 = storage_service.generate_presigned_put_url(
            user_id=1, content_type="image/jpeg", file_size=100
        )
        _, key2 = storage_service.generate_presigned_put_url(
            user_id=1, content_type="image/jpeg", file_size=100
        )

        assert key1 != key2


class TestGeneratePresignedGetUrl:
    """Tests for generate_presigned_get_url."""

    def test_valid_object_key(self, storage_service: StorageService) -> None:
        """Test presigned GET URL generation with valid key."""
        key = "uploads/42/550e8400-e29b-41d4-a716-446655440000.jpg"
        get_url = storage_service.generate_presigned_get_url(key)

        assert get_url.startswith("https://")

        mock_client = storage_service._mock_client  # type: ignore[attr-defined]
        call_args = mock_client.generate_presigned_url.call_args
        assert call_args[0][0] == "get_object"
        params = call_args[1]["Params"]
        assert params["Key"] == key
        assert call_args[1]["ExpiresIn"] == 3600

    def test_invalid_object_key(self, storage_service: StorageService) -> None:
        """Test rejection of invalid object key."""
        with pytest.raises(ValueError, match="Invalid object key"):
            storage_service.generate_presigned_get_url("../../etc/passwd")

    def test_base64_data_uri_rejected(self, storage_service: StorageService) -> None:
        """Test that base64 data URIs are rejected as object keys."""
        with pytest.raises(ValueError, match="Invalid object key"):
            storage_service.generate_presigned_get_url(
                "data:image/jpeg;base64,/9j/4AAQ..."
            )


class TestReplaceObjectKeysWithUrls:
    """Tests for _replace_object_keys_with_urls in generation service."""

    def test_replaces_object_keys(self) -> None:
        """Test that valid object keys are replaced with presigned GET URLs."""
        from app.services.generation import _replace_object_keys_with_urls

        mock_storage = MagicMock()
        mock_storage.generate_presigned_get_url.return_value = (
            "https://account-id.r2.cloudflarestorage.com/signed-get"
        )

        input_data = {
            "prompt": "test",
            "image_input": [
                "uploads/1/550e8400-e29b-41d4-a716-446655440000.jpg",
            ],
        }

        with patch(
            "services.storage.get_storage_service",
            return_value=mock_storage,
        ):
            result = _replace_object_keys_with_urls(input_data)

        assert result["prompt"] == "test"
        assert result["image_input"] == [
            "https://account-id.r2.cloudflarestorage.com/signed-get"
        ]
        mock_storage.generate_presigned_get_url.assert_called_once_with(
            "uploads/1/550e8400-e29b-41d4-a716-446655440000.jpg"
        )

    def test_base64_passthrough(self) -> None:
        """Test that base64 data URIs pass through unchanged."""
        from app.services.generation import _replace_object_keys_with_urls

        mock_storage = MagicMock()

        input_data = {
            "prompt": "test",
            "image_input": [
                "data:image/jpeg;base64,/9j/4AAQSkZJRg...",
            ],
        }

        with patch(
            "services.storage.get_storage_service",
            return_value=mock_storage,
        ):
            result = _replace_object_keys_with_urls(input_data)

        # Base64 URIs don't match OBJECT_KEY_PATTERN, so they pass through
        assert result["image_input"] == [
            "data:image/jpeg;base64,/9j/4AAQSkZJRg...",
        ]
        mock_storage.generate_presigned_get_url.assert_not_called()

    def test_non_list_values_unchanged(self) -> None:
        """Test that non-list values are not modified."""
        from app.services.generation import _replace_object_keys_with_urls

        mock_storage = MagicMock()

        input_data = {
            "prompt": "test prompt",
            "seed": 42,
            "style": "anime",
        }

        with patch(
            "services.storage.get_storage_service",
            return_value=mock_storage,
        ):
            result = _replace_object_keys_with_urls(input_data)

        assert result == input_data
        mock_storage.generate_presigned_get_url.assert_not_called()

    def test_mixed_list_not_replaced(self) -> None:
        """Test that a list with mixed valid/invalid keys is not replaced."""
        from app.services.generation import _replace_object_keys_with_urls

        mock_storage = MagicMock()

        input_data = {
            "image_input": [
                "uploads/1/550e8400-e29b-41d4-a716-446655440000.jpg",
                "not-a-valid-key",
            ],
        }

        with patch(
            "services.storage.get_storage_service",
            return_value=mock_storage,
        ):
            result = _replace_object_keys_with_urls(input_data)

        # Mixed list: not all items match, so nothing is replaced
        assert result["image_input"] == input_data["image_input"]
        mock_storage.generate_presigned_get_url.assert_not_called()
