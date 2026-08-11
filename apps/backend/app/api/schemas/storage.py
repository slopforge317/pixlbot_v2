"""Storage schemas for presigned URL endpoints."""

from pydantic import BaseModel, Field


class PresignUploadRequest(BaseModel):
    """Request to get a presigned PUT URL for uploading."""

    content_type: str = Field(
        ..., description="MIME type: image/jpeg, image/png, or image/webp"
    )
    file_size: int = Field(..., gt=0, description="File size in bytes")


class PresignUploadResponse(BaseModel):
    """Response with presigned PUT URL for direct upload."""

    upload_url: str = Field(..., description="Presigned PUT URL for R2 upload")
    object_key: str = Field(..., description="R2 object key for referencing")
    content_type: str = Field(
        ..., description="Content type (echo back for PUT header)"
    )
