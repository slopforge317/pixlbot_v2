from db.base import Base
from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column


class CreditPackage(Base):
    """Пакет кредитов для покупки."""

    __tablename__ = "credit_packages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    credit_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    fiat_price: Mapped[int] = mapped_column(Integer, nullable=False)  # в копейках
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<CreditPackage {self.name} credits={self.credit_amount}>"
