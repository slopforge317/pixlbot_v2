from typing import TYPE_CHECKING, Any

from db.base import Base
from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from db.models.pricing_variant import PricingVariant
    from db.models.provider import Provider


class AIModel(Base):
    """AI model within a provider (e.g. seedream/4.5-text-to-image)."""

    __tablename__ = "ai_models"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    provider_id: Mapped[int] = mapped_column(
        ForeignKey("providers.id"), nullable=False, index=True
    )
    api_model_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    input_schema: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    variant_keys: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, server_default="0"
    )
    status: Mapped[str | None] = mapped_column(String(20), nullable=True, default=None)

    # Relationships
    provider: Mapped["Provider"] = relationship(back_populates="models")
    pricing_variants: Mapped[list["PricingVariant"]] = relationship(
        back_populates="model"
    )

    def __repr__(self) -> str:
        return f"<AIModel {self.api_model_id} title={self.title}>"
