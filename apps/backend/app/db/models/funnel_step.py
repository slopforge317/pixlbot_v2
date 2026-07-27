from db.base import Base, TimestampMixin
from db.enums import FunnelCondition, FunnelTriggerEvent
from sqlalchemy import Boolean, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column


class FunnelStep(Base, TimestampMixin):
    """Шаг воронки — загружается из YAML-конфига."""

    __tablename__ = "funnel_steps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    trigger_event: Mapped[FunnelTriggerEvent] = mapped_column(
        Enum(FunnelTriggerEvent, native_enum=False), nullable=False
    )
    delay_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    condition: Mapped[FunnelCondition | None] = mapped_column(
        Enum(FunnelCondition, native_enum=False), nullable=True
    )
    message_text: Mapped[str] = mapped_column(Text, nullable=False)
    button_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    button_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    def __repr__(self) -> str:
        return f"<FunnelStep {self.id} name={self.name}>"
