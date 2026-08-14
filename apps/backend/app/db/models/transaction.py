from typing import TYPE_CHECKING

from db.base import Base, TimestampMixin
from db.enums import TransactionType
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from db.models.credit_package import CreditPackage
    from db.models.generation_job import GenerationJob
    from db.models.payment import Payment
    from db.models.user import User


class Transaction(Base, TimestampMixin):
    """Транзакция кредитов (immutable ledger)."""

    __tablename__ = "transactions"
    __table_args__ = (
        UniqueConstraint("payment_id", name="uq_transactions_payment_id"),
    )

    tx_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.user_id"), nullable=False, index=True
    )
    type: Mapped[TransactionType] = mapped_column(
        SQLEnum(TransactionType, native_enum=False), nullable=False
    )
    amount_credits: Mapped[int] = mapped_column(Integer, nullable=False)

    # Nullable FKs (полиморфная связь - заполняется одно из полей)
    job_id: Mapped[int | None] = mapped_column(
        ForeignKey("generations_job.job_id"), nullable=True
    )
    payment_id: Mapped[int | None] = mapped_column(
        ForeignKey("payments.payment_id"), nullable=True
    )
    credit_package_id: Mapped[int | None] = mapped_column(
        ForeignKey("credit_packages.id"), nullable=True
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="transactions")
    job: Mapped["GenerationJob | None"] = relationship(back_populates="transactions")
    payment: Mapped["Payment | None"] = relationship(back_populates="transactions")
    credit_package: Mapped["CreditPackage | None"] = relationship()

    def __repr__(self) -> str:
        return (
            f"<Transaction {self.tx_id} "
            f"type={self.type.value} amount={self.amount_credits}>"
        )
