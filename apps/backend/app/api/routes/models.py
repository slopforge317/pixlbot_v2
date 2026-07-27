"""Providers API endpoints."""

from api.deps import CurrentUser, DBSession
from api.schemas.ai_model import (
    AIModelResponse,
    PricingVariantResponse,
    ProviderListResponse,
    ProviderResponse,
)
from db.models.provider import Provider
from db.repositories.provider import ProviderRepository
from fastapi import APIRouter, Query
from loguru import logger

router = APIRouter(prefix="/api", tags=["providers"])


def _provider_to_response(provider: Provider) -> ProviderResponse:
    """Convert Provider ORM object to response with nested models and pricing."""
    models = []
    for model in sorted(provider.models, key=lambda m: (m.sort_order, m.id)):
        pricing = [
            PricingVariantResponse(
                id=pv.id,
                variant_values=pv.variant_values,
                price=pv.price,
            )
            for pv in model.pricing_variants
        ]
        models.append(
            AIModelResponse(
                id=model.id,
                api_model_id=model.api_model_id,
                title=model.title,
                input_schema=model.input_schema,
                variant_keys=model.variant_keys,
                pricing=pricing,
                status=model.status,
            )
        )
    return ProviderResponse(
        id=provider.id,
        title=provider.title,
        gen_type=provider.gen_type,
        models=models,
    )


@router.get("/providers", response_model=ProviderListResponse)
async def list_providers(
    user: CurrentUser,
    session: DBSession,
    gen_type: str | None = Query(None, description="Filter by gen_type (image/video)"),
) -> ProviderListResponse:
    """
    Get list of providers with their models and pricing variants.

    Optionally filter by gen_type (image/video).
    Requires: Authorization: tma <initData>
    """
    logger.debug(f"Listing providers: user_id={user.user_id}, gen_type={gen_type}")
    repo = ProviderRepository(session)

    if gen_type:
        providers = await repo.get_by_gen_type(gen_type)
    else:
        providers = await repo.get_all_active_with_models()

    return ProviderListResponse(providers=[_provider_to_response(p) for p in providers])
