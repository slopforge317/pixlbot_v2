from datetime import datetime
from typing import TYPE_CHECKING, Any

from db.base import Base, TimestampMixin
from db.enums import PaymentStatus
from sqlalchemy import JSON, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from db.models.credit_package import CreditPackage
    from db.models.transaction import Transaction
    from db.models.user import User


class Payment(Base, TimestampMixin):
    """Платёж от пользователя (фиатные деньги)."""

    __tablename__ = "payments"

    payment_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.user_id"), nullable=False, index=True
    )
    status: Mapped[PaymentStatus] = mapped_column(
        SQLEnum(PaymentStatus, native_enum=False),
        default=PaymentStatus.pending,
        nullable=False,
    )
    amount_currency: Mapped[int] = mapped_column(Integer, nullable=False)  # в копейках
    credits_amount: Mapped[int | None] = mapped_column(Integer, nullable=True)
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, default="RUB", server_default="RUB"
    )
    details: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    yookassa_payment_id: Mapped[str | None] = mapped_column(
        String(50), unique=True, index=True, nullable=True
    )
    credit_package_id: Mapped[int | None] = mapped_column(
        ForeignKey("credit_packages.id"), nullable=True
    )
    invoice_payload: Mapped[str | None] = mapped_column(
        String(128), unique=True, index=True, nullable=True
    )
    telegram_payment_charge_id: Mapped[str | None] = mapped_column(
        String(255), unique=True, index=True, nullable=True
    )
    provider_payment_charge_id: Mapped[str | None] = mapped_column(
        String(255), unique=True, index=True, nullable=True
    )
    customer_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="payments")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="payment")
    credit_package: Mapped["CreditPackage | None"] = relationship()

    def __repr__(self) -> str:
        return f"<Payment {self.payment_id} status={self.status.value}>"
