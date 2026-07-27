from db.models.ai_model import AIModel
from db.models.pricing_variant import PricingVariant
from db.models.provider import Provider
from db.repositories.base import BaseRepository
from sqlalchemy import select
from sqlalchemy.orm import selectinload


class ProviderRepository(BaseRepository[Provider]):
    """Repository for Provider operations."""

    model = Provider

    async def get_all_active_with_models(self) -> list[Provider]:
        """Get all active providers with active models and active pricing variants."""
        stmt = (
            select(Provider)
            .where(Provider.active == True)  # noqa: E712
            .options(
                selectinload(
                    Provider.models.and_(AIModel.active == True)  # noqa: E712
                ).selectinload(
                    AIModel.pricing_variants.and_(
                        PricingVariant.active == True  # noqa: E712
                    )
                )
            )
            .order_by(Provider.sort_order, Provider.id)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().unique().all())

    async def get_by_gen_type(self, gen_type: str) -> list[Provider]:
        """Get active providers filtered by gen_type (image/video)."""
        stmt = (
            select(Provider)
            .where(
                Provider.gen_type == gen_type,
                Provider.active == True,  # noqa: E712
            )
            .options(
                selectinload(
                    Provider.models.and_(AIModel.active == True)  # noqa: E712
                ).selectinload(
                    AIModel.pricing_variants.and_(
                        PricingVariant.active == True  # noqa: E712
                    )
                )
            )
            .order_by(Provider.sort_order, Provider.id)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().unique().all())
