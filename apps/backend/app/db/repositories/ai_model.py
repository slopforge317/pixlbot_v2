from db.models.ai_model import AIModel
from db.models.pricing_variant import PricingVariant
from db.repositories.base import BaseRepository
from sqlalchemy import select
from sqlalchemy.orm import selectinload


class AiModelRepository(BaseRepository[AIModel]):
    """Repository for AIModel operations."""

    model = AIModel

    async def get_by_api_model_id(self, api_model_id: str) -> AIModel | None:
        """Get model by its API model ID (e.g. 'seedream/4.5-edit')."""
        stmt = select(AIModel).where(AIModel.api_model_id == api_model_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_with_variants(self, model_id: int) -> AIModel | None:
        """Get model by ID with active pricing variants."""
        stmt = (
            select(AIModel)
            .where(AIModel.id == model_id)
            .options(
                selectinload(
                    AIModel.pricing_variants.and_(
                        PricingVariant.active == True  # noqa: E712
                    )
                )
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
