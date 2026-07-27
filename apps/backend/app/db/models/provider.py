from typing import TYPE_CHECKING

from db.base import Base
from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from db.models.ai_model import AIModel


class Provider(Base):
    """AI provider (e.g. Nano Banana Pro, Seedream 4.5)."""

    __tablename__ = "providers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    gen_type: Mapped[str] = mapped_column(String(20), nullable=False)  # "image"/"video"
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, server_default="0"
    )

    # Relationships
    models: Mapped[list["AIModel"]] = relationship(back_populates="provider")

    def __repr__(self) -> str:
        return f"<Provider {self.title} gen_type={self.gen_type}>"
