"""S3-compatible storage service for presigned URL generation."""

import re
from uuid import uuid4

import boto3
from botocore.config import Config
from core.config import settings
from loguru import logger

# Allowed upload content types and their file extensions
ALLOWED_CONTENT_TYPES: dict[str, str] = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}

# Regex for validating object keys — prevents path traversal
_UUID_HEX = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
OBJECT_KEY_PATTERN = re.compile(rf"^uploads/\d+/{_UUID_HEX}\.(jpg|png|webp)$")


class StorageService:
    """Service for generating presigned S3 URLs."""

    def __init__(
        self,
        access_key_id: str,
        secret_access_key: str,
        bucket_name: str,
        endpoint_url: str,
        region: str,
        upload_max_size_bytes: int,
        presign_upload_expires: int,
        presign_download_expires: int,
    ) -> None:
        self._bucket_name = bucket_name
        self._upload_max_size_bytes = upload_max_size_bytes
        self._presign_upload_expires = presign_upload_expires
        self._presign_download_expires = presign_download_expires

        self._client = boto3.client(
            "s3",
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            endpoint_url=endpoint_url,
            region_name=region,
            config=Config(signature_version="s3v4"),
        )

    def generate_presigned_put_url(
        self,
        user_id: int,
        content_type: str,
        file_size: int,
    ) -> tuple[str, str]:
        """Generate a presigned PUT URL for direct upload.

        Args:
            user_id: ID of the uploading user (for key namespacing)
            content_type: MIME type of the file
            file_size: File size in bytes

        Returns:
            Tuple of (presigned_put_url, object_key)

        Raises:
            ValueError: If content_type or file_size is invalid
        """
        if content_type not in ALLOWED_CONTENT_TYPES:
            allowed = ", ".join(sorted(ALLOWED_CONTENT_TYPES.keys()))
            raise ValueError(
                f"Unsupported content type: {content_type}. Allowed: {allowed}"
            )

        if file_size <= 0:
            raise ValueError("File size must be positive")

        if file_size > self._upload_max_size_bytes:
            max_mb = self._upload_max_size_bytes / (1024 * 1024)
            raise ValueError(f"File size exceeds maximum of {max_mb:.0f} MB")

        ext = ALLOWED_CONTENT_TYPES[content_type]
        object_key = f"uploads/{user_id}/{uuid4()}.{ext}"

        put_url = self._client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": self._bucket_name,
                "Key": object_key,
                "ContentType": content_type,
            },
            ExpiresIn=self._presign_upload_expires,
        )

        logger.debug(
            f"Generated presigned PUT URL: user_id={user_id}, key={object_key}"
        )
        return put_url, object_key

    def generate_presigned_get_url(self, object_key: str) -> str:
        """Generate a presigned GET URL for downloading an object.

        Args:
            object_key: S3 object key

        Returns:
            Presigned GET URL

        Raises:
            ValueError: If object_key doesn't match expected pattern
        """
        if not is_valid_object_key(object_key):
            raise ValueError(f"Invalid object key: {object_key}")

        get_url = self._client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": self._bucket_name,
                "Key": object_key,
            },
            ExpiresIn=self._presign_download_expires,
        )

        return get_url


def is_valid_object_key(object_key: str) -> bool:
    """Check if an object key matches the expected pattern.

    Args:
        object_key: S3 object key to validate

    Returns:
        True if valid, False otherwise
    """
    return bool(OBJECT_KEY_PATTERN.match(object_key))


# Lazy singleton
_storage_service: StorageService | None = None


def get_storage_service() -> StorageService:
    """Get or create the StorageService singleton.

    Returns:
        StorageService instance

    Raises:
        RuntimeError: If S3 is not configured
    """
    global _storage_service
    if _storage_service is not None:
        return _storage_service

    if not settings.s3_access_key_id or not settings.s3_bucket_name:
        raise RuntimeError(
            "S3 storage is not configured. "
            "Set S3_ACCESS_KEY_ID and S3_BUCKET_NAME in .env"
        )

    _storage_service = StorageService(
        access_key_id=settings.s3_access_key_id,
        secret_access_key=settings.s3_secret_access_key,
        bucket_name=settings.s3_bucket_name,
        endpoint_url=settings.s3_endpoint_url,
        region=settings.s3_region,
        upload_max_size_bytes=settings.s3_upload_max_size_bytes,
        presign_upload_expires=settings.s3_presign_upload_expires,
        presign_download_expires=settings.s3_presign_download_expires,
    )

    logger.info(
        f"StorageService initialized: bucket={settings.s3_bucket_name}, "
        f"endpoint={settings.s3_endpoint_url}"
    )
    return _storage_service
