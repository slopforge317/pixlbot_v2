import re
from typing import TYPE_CHECKING, Any

from db.base import Base
from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from db.models.ai_model import AIModel


def _default_slug(context: Any) -> str:
    """Build a fallback slug for non-catalog ORM records, mainly test fixtures."""
    title = str(context.get_current_parameters().get("title", "provider"))
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug or "provider"


class Provider(Base):
    """AI provider (e.g. Nano Banana Pro, Seedream 4.5)."""

    __tablename__ = "providers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, default=_default_slug
    )
    title: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    gen_type: Mapped[str] = mapped_column(String(20), nullable=False)  # "image"/"video"
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, server_default="0"
    )

    # Relationships
    models: Mapped[list["AIModel"]] = relationship(back_populates="provider")

    def __repr__(self) -> str:
        return f"<Provider {self.slug} title={self.title} gen_type={self.gen_type}>"
