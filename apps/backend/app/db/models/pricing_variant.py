from typing import TYPE_CHECKING, Any

from db.base import Base
from sqlalchemy import JSON, Boolean, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from db.models.ai_model import AIModel
    from db.models.generation_job import GenerationJob


class PricingVariant(Base):
    """Pricing variant for an AI model (combination of variant parameters)."""

    __tablename__ = "pricing_variants"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    model_id: Mapped[int] = mapped_column(
        ForeignKey("ai_models.id"), nullable=False, index=True
    )
    variant_values: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    price: Mapped[int] = mapped_column(Integer, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    model: Mapped["AIModel"] = relationship(back_populates="pricing_variants")
    generation_jobs: Mapped[list["GenerationJob"]] = relationship(
        back_populates="pricing_variant"
    )

    def __repr__(self) -> str:
        return f"<PricingVariant model_id={self.model_id} price={self.price}>"
