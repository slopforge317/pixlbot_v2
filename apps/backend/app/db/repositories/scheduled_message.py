from datetime import datetime, timezone

from db.enums import ScheduledMessageStatus
from db.models.scheduled_message import ScheduledMessage
from db.repositories.base import BaseRepository
from sqlalchemy import select
from sqlalchemy.orm import selectinload


class ScheduledMessageRepository(BaseRepository[ScheduledMessage]):
    """Repository for ScheduledMessage operations."""

    model = ScheduledMessage

    async def get_due_pending(self, limit: int = 100) -> list[ScheduledMessage]:
        """Get pending messages whose scheduled_at is in the past."""
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        stmt = (
            select(ScheduledMessage)
            .options(selectinload(ScheduledMessage.funnel_step))
            .where(
                ScheduledMessage.status == ScheduledMessageStatus.pending,
                ScheduledMessage.scheduled_at <= now,
            )
            .order_by(ScheduledMessage.scheduled_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
