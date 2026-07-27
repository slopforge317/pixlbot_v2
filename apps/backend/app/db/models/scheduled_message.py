from datetime import datetime
from typing import TYPE_CHECKING

from db.base import Base, TimestampMixin
from db.enums import ScheduledMessageStatus
from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from db.models.funnel_step import FunnelStep
    from db.models.user import User


class ScheduledMessage(Base, TimestampMixin):
    """Запланированное сообщение воронки для конкретного пользователя."""

    __tablename__ = "scheduled_messages"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "funnel_step_id", name="uq_scheduled_message_user_step"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    funnel_step_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("funnel_steps.id", ondelete="CASCADE"), nullable=False
    )
    scheduled_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[ScheduledMessageStatus] = mapped_column(
        Enum(ScheduledMessageStatus),
        nullable=False,
        default=ScheduledMessageStatus.pending,
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="scheduled_messages")
    funnel_step: Mapped["FunnelStep"] = relationship()

    def __repr__(self) -> str:
        return (
            f"<ScheduledMessage {self.id} user_id={self.user_id} "
            f"step_id={self.funnel_step_id} status={self.status}>"
        )
