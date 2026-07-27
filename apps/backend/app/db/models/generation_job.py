from datetime import datetime
from typing import TYPE_CHECKING, Any

from db.base import Base, TimestampMixin
from db.enums import JobStatus
from sqlalchemy import JSON, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from db.models.pricing_variant import PricingVariant
    from db.models.transaction import Transaction
    from db.models.user import User


class GenerationJob(Base, TimestampMixin):
    """Задача на генерацию контента."""

    __tablename__ = "generations_job"

    job_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.user_id"), nullable=False, index=True
    )
    pricing_variant_id: Mapped[int] = mapped_column(
        ForeignKey("pricing_variants.id"), nullable=False, index=True
    )
    status: Mapped[JobStatus] = mapped_column(
        SQLEnum(JobStatus, native_enum=False),
        default=JobStatus.queue,
        nullable=False,
        index=True,
    )
    provider_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider_complete_time: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    provider_consume_credit: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    cost_credit: Mapped[int] = mapped_column(Integer, nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    generation_params: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    references_meta: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    success_url_asset: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    telegram_file_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="generation_jobs")
    pricing_variant: Mapped["PricingVariant"] = relationship(
        back_populates="generation_jobs"
    )
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="job")

    def __repr__(self) -> str:
        return f"<GenerationJob {self.job_id} status={self.status.value}>"
