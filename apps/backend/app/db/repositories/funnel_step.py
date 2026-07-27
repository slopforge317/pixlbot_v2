from db.enums import FunnelTriggerEvent
from db.models.funnel_step import FunnelStep
from db.repositories.base import BaseRepository
from sqlalchemy import select


class FunnelStepRepository(BaseRepository[FunnelStep]):
    """Repository for FunnelStep operations."""

    model = FunnelStep

    async def get_by_name(self, name: str) -> FunnelStep | None:
        """Get funnel step by unique name."""
        stmt = select(FunnelStep).where(FunnelStep.name == name)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_by_trigger(
        self, trigger_event: FunnelTriggerEvent
    ) -> list[FunnelStep]:
        """Get all active funnel steps for a given trigger event."""
        stmt = select(FunnelStep).where(
            FunnelStep.trigger_event == trigger_event,
            FunnelStep.is_active.is_(True),
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
