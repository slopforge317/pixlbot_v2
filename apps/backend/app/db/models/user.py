from typing import TYPE_CHECKING

from db.base import Base, TimestampMixin
from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from db.models.generation_job import GenerationJob
    from db.models.payment import Payment
    from db.models.scheduled_message import ScheduledMessage
    from db.models.transaction import Transaction


class User(Base, TimestampMixin):
    """Пользователь бота."""

    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_user_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, index=True, nullable=False
    )
    first_name: Mapped[str] = mapped_column(String(255), nullable=False)
    last_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    utm_source: Mapped[str] = mapped_column(
        String(100), default="direct", nullable=False
    )

    # Relationships
    payments: Mapped[list["Payment"]] = relationship(back_populates="user")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="user")
    generation_jobs: Mapped[list["GenerationJob"]] = relationship(back_populates="user")
    scheduled_messages: Mapped[list["ScheduledMessage"]] = relationship(
        back_populates="user"
    )

    def __repr__(self) -> str:
        return f"<User {self.user_id} tg={self.telegram_user_id}>"
