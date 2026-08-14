from datetime import datetime
from typing import Any

from db.enums import PaymentStatus
from db.models.payment import Payment
from db.repositories.base import BaseRepository
from sqlalchemy import select


class PaymentRepository(BaseRepository[Payment]):
    """Repository for Payment operations."""

    model = Payment

    async def get_by_invoice_payload(
        self,
        invoice_payload: str,
        *,
        for_update: bool = False,
    ) -> Payment | None:
        """Find a Telegram invoice payment by its opaque payload."""
        stmt = select(Payment).where(Payment.invoice_payload == invoice_payload)
        if for_update:
            stmt = stmt.with_for_update()
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_pending(
        self,
        user_id: int,
        amount_currency: int,
        credit_package_id: int,
        credits_amount: int,
        invoice_payload: str,
        currency: str = "RUB",
    ) -> Payment:
        """Create a pending Telegram invoice payment with immutable snapshots."""
        return await self.create(
            user_id=user_id,
            amount_currency=amount_currency,
            credits_amount=credits_amount,
            currency=currency,
            credit_package_id=credit_package_id,
            status=PaymentStatus.pending,
            invoice_payload=invoice_payload,
        )

    async def mark_success(
        self,
        payment: Payment,
        *,
        telegram_payment_charge_id: str,
        provider_payment_charge_id: str,
        customer_email: str,
        details: dict[str, Any],
    ) -> Payment:
        """Mark a Telegram payment as successful."""
        return await self.update(
            payment,
            status=PaymentStatus.success,
            telegram_payment_charge_id=telegram_payment_charge_id,
            provider_payment_charge_id=provider_payment_charge_id,
            customer_email=customer_email,
            paid_at=datetime.utcnow(),
            details=details,
        )

    async def mark_failed(self, payment: Payment, details: dict[str, Any]) -> Payment:
        """Mark payment as failed."""
        return await self.update(payment, status=PaymentStatus.failed, details=details)
