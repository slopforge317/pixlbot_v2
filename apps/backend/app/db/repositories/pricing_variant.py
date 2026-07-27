from db.models.ai_model import AIModel
from db.models.pricing_variant import PricingVariant
from db.repositories.base import BaseRepository
from sqlalchemy import select
from sqlalchemy.orm import selectinload


class PricingVariantRepository(BaseRepository[PricingVariant]):
    """Repository for PricingVariant operations."""

    model = PricingVariant

    async def get_by_id_with_model(self, variant_id: int) -> PricingVariant | None:
        """Get pricing variant by ID with eager-loaded model and provider."""
        stmt = (
            select(PricingVariant)
            .where(PricingVariant.id == variant_id)
            .options(selectinload(PricingVariant.model).selectinload(AIModel.provider))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_by_model_id(self, model_id: int) -> list[PricingVariant]:
        """Get active pricing variants for a specific model."""
        stmt = select(PricingVariant).where(
            PricingVariant.model_id == model_id,
            PricingVariant.active == True,  # noqa: E712
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
