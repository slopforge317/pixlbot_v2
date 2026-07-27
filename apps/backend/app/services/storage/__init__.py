"""Storage service for S3-compatible object storage."""

from services.storage.service import StorageService, get_storage_service

__all__ = ["StorageService", "get_storage_service"]
