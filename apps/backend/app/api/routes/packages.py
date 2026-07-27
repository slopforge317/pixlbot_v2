"""Credit Packages API endpoints."""

from api.deps import CurrentUser, DBSession
from api.schemas.credit_package import CreditPackageListResponse, CreditPackageResponse
from db.repositories.credit_package import CreditPackageRepository
from fastapi import APIRouter
from loguru import logger

router = APIRouter(prefix="/api", tags=["packages"])


@router.get("/packages", response_model=CreditPackageListResponse)
async def list_packages(
    user: CurrentUser,
    session: DBSession,
) -> CreditPackageListResponse:
    """
    Get list of available credit packages for purchase.

    Packages are sorted by price (ascending).
    Requires: Authorization: tma <initData>
    """
    logger.debug(f"Listing packages: user_id={user.user_id}")
    repo = CreditPackageRepository(session)
    packages = await repo.get_active_ordered_by_price()

    return CreditPackageListResponse(
        packages=[CreditPackageResponse.model_validate(p) for p in packages]
    )
