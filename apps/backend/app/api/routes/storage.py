"""Storage routes for presigned URL generation."""

from api.deps import CurrentUser
from api.schemas.storage import PresignUploadRequest, PresignUploadResponse
from fastapi import APIRouter, HTTPException, status
from loguru import logger
from services.storage import get_storage_service

router = APIRouter(prefix="/api/storage", tags=["storage"])


@router.post(
    "/presign-upload",
    response_model=PresignUploadResponse,
    status_code=status.HTTP_200_OK,
)
async def presign_upload(
    request: PresignUploadRequest,
    user: CurrentUser,
) -> PresignUploadResponse:
    """Get a presigned PUT URL for uploading a file to Cloudflare R2.

    The client should PUT the file directly to the returned URL
    with the specified Content-Type header.
    """
    try:
        storage = get_storage_service()
    except RuntimeError as e:
        logger.error(f"Storage service not available: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Storage service is not configured",
        )

    try:
        upload_url, object_key = storage.generate_presigned_put_url(
            user_id=user.user_id,
            content_type=request.content_type,
            file_size=request.file_size,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    logger.info(
        f"Presigned upload URL generated: user_id={user.user_id}, key={object_key}"
    )

    return PresignUploadResponse(
        upload_url=upload_url,
        object_key=object_key,
        content_type=request.content_type,
    )
