from datetime import datetime
from typing import Any

from db.enums import PaymentStatus
from db.models.payment import Payment
from db.repositories.base import BaseRepository
from sqlalchemy import select


class PaymentRepository(BaseRepository[Payment]):
    """Repository for Payment operations."""

    model = Payment

    async def get_by_yookassa_id(self, yookassa_payment_id: str) -> Payment | None:
        """Find payment by YooKassa payment ID."""
        stmt = select(Payment).where(Payment.yookassa_payment_id == yookassa_payment_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_pending(
        self,
        user_id: int,
        amount_currency: int,
        credit_package_id: int,
        yookassa_payment_id: str | None = None,
    ) -> Payment:
        """Create a pending payment."""
        return await self.create(
            user_id=user_id,
            amount_currency=amount_currency,
            credit_package_id=credit_package_id,
            status=PaymentStatus.pending,
            yookassa_payment_id=yookassa_payment_id,
        )

    async def mark_success(self, payment: Payment, details: dict[str, Any]) -> Payment:
        """Mark payment as successful."""
        return await self.update(payment, status=PaymentStatus.success, details=details)

    async def mark_failed(self, payment: Payment, details: dict[str, Any]) -> Payment:
        """Mark payment as failed."""
        return await self.update(payment, status=PaymentStatus.failed, details=details)

    async def get_stale_pending(
        self, older_than: datetime, limit: int = 50
    ) -> list[Payment]:
        """Find pending payments older than given time with a YooKassa ID."""
        stmt = (
            select(Payment)
            .where(
                Payment.status == PaymentStatus.pending,
                Payment.created_at < older_than,
                Payment.yookassa_payment_id.isnot(None),
            )
            .order_by(Payment.created_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
