"""Payment service for YooKassa integration."""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Any

from async_yookassa import YooKassaClient
from async_yookassa.models.payment.amount import Amount
from async_yookassa.models.payment.confirmation import (
    ConfirmationType,
    RedirectConfirmation,
    RedirectConfirmationRequest,
)
from async_yookassa.models.payment.receipts.base import Receipt
from async_yookassa.models.payment.receipts.customer import Customer
from async_yookassa.models.payment.receipts.receipt_item import ReceiptItemBase
from async_yookassa.models.payment.request import PaymentRequest
from bot import create_bot
from core.config import settings
from db.enums import PaymentStatus
from db.models.credit_package import CreditPackage
from db.models.payment import Payment
from db.models.transaction import Transaction
from db.repositories.payment import PaymentRepository
from db.repositories.transaction import TransactionRepository
from db.repositories.user import UserRepository
from db.session import get_session
from loguru import logger
from services.notification import send_payment_success
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


def _create_client() -> YooKassaClient:
    """Create a YooKassa API client."""
    return YooKassaClient(
        account_id=settings.yookassa_shop_id,
        secret_key=settings.yookassa_secret_key,
    )


def kopeks_to_rubles(kopeks: int) -> str:
    """Convert kopeks to rubles string: 9900 -> '99.00'."""
    return f"{kopeks / 100:.2f}"


async def create_yookassa_payment(
    amount_kopeks: int,
    description: str,
    return_url: str,
    metadata: dict[str, str],
    email: str,
    idempotency_key: str | None = None,
) -> tuple[str, str]:
    """Create a payment in YooKassa.

    Returns:
        Tuple of (yookassa_payment_id, confirmation_url)
    """
    amount = Amount(value=kopeks_to_rubles(amount_kopeks), currency="RUB")

    receipt = Receipt(
        customer=Customer(email=email),
        items=[
            ReceiptItemBase(
                description=description,
                amount=amount,
                vat_code=settings.yookassa_vat_code,
                quantity="1",
                payment_subject="service",
                payment_mode="full_payment",
            )
        ],
        tax_system_code=settings.yookassa_tax_system_code,
    )

    payment_data = PaymentRequest(
        amount=amount,
        receipt=receipt,
        confirmation=RedirectConfirmationRequest(
            type=ConfirmationType.redirect, return_url=return_url
        ),
        capture=True,
        description=description,
        metadata=metadata,
    )

    # Generate deterministic UUID from payment_id for idempotency
    if idempotency_key:
        key = uuid.uuid5(uuid.NAMESPACE_URL, f"pixlbot:payment:{idempotency_key}")
    else:
        key = uuid.uuid4()
    async with _create_client() as client:
        response = await client.payment.create(payment_data, key)

    yookassa_id: str = response.id
    confirmation = response.confirmation
    assert isinstance(confirmation, RedirectConfirmation)
    confirmation_url: str = confirmation.confirmation_url

    logger.info(
        f"YooKassa payment created: id={yookassa_id}, "
        f"amount={kopeks_to_rubles(amount_kopeks)} RUB"
    )
    return yookassa_id, confirmation_url


async def process_yookassa_notification(
    event: str,
    yookassa_payment_id: str,
    payment_data: dict[str, Any],
) -> None:
    """Process YooKassa webhook notification.

    Creates its own DB session since this runs as a background task.
    """
    logger.info(
        f"Processing YooKassa notification: event={event}, "
        f"yookassa_id={yookassa_payment_id}"
    )

    async with get_session() as session:
        payment_repo = PaymentRepository(session)
        payment = await payment_repo.get_by_yookassa_id(yookassa_payment_id)

        if not payment:
            logger.warning(f"Payment not found for yookassa_id={yookassa_payment_id}")
            return

        # Idempotency: skip if already processed
        if payment.status != PaymentStatus.pending:
            logger.info(
                f"Payment {payment.payment_id} already processed "
                f"(status={payment.status.value}), skipping"
            )
            return

        if event == "payment.succeeded":
            await _handle_payment_succeeded(
                session, payment_repo, payment, payment_data
            )
        elif event == "payment.canceled":
            await payment_repo.mark_failed(payment, payment_data)
            logger.info(f"Payment {payment.payment_id} marked as failed (canceled)")
        else:
            logger.warning(f"Unknown YooKassa event: {event}")


async def _handle_payment_succeeded(
    session: AsyncSession,
    payment_repo: PaymentRepository,
    payment: Payment,
    payment_data: dict[str, Any],
) -> None:
    """Handle successful payment: update status, create deposit, notify."""
    # Defense in depth: verify with YooKassa API
    assert payment.yookassa_payment_id is not None
    try:
        async with _create_client() as client:
            yookassa_payment = await client.payment.find_one(
                payment.yookassa_payment_id
            )
        if yookassa_payment.status != "succeeded":
            logger.warning(
                f"YooKassa verification failed for payment "
                f"{payment.payment_id}: status={yookassa_payment.status}"
            )
            return
    except Exception as e:
        logger.error(
            f"Failed to verify payment {payment.payment_id} " f"with YooKassa: {e}"
        )
        # Continue processing — webhook data is trusted (IP-verified)

    await payment_repo.mark_success(payment, payment_data)

    # Get credit package info
    if not payment.credit_package_id:
        logger.error(f"Payment {payment.payment_id} has no credit_package_id")
        return

    credit_package = await session.get(CreditPackage, payment.credit_package_id)
    if not credit_package:
        logger.error(
            f"CreditPackage {payment.credit_package_id} not found "
            f"for payment {payment.payment_id}"
        )
        return

    # Create deposit transaction
    tx_repo = TransactionRepository(session)
    await tx_repo.create_deposit(
        user_id=payment.user_id,
        amount_credits=credit_package.credit_amount,
        payment_id=payment.payment_id,
        credit_package_id=payment.credit_package_id,
    )

    logger.info(
        f"Deposit created: user_id={payment.user_id}, "
        f"credits={credit_package.credit_amount}, "
        f"payment_id={payment.payment_id}"
    )

    # Get updated balance and notify via Telegram
    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(payment.user_id)
    if not user:
        logger.error(f"User {payment.user_id} not found for payment notification")
        return

    # Calculate new balance from transactions
    balance_stmt = select(func.coalesce(func.sum(Transaction.amount_credits), 0)).where(
        Transaction.user_id == payment.user_id
    )
    result = await session.execute(balance_stmt)
    new_balance: int = result.scalar_one()

    bot = create_bot()
    try:
        await send_payment_success(
            bot=bot,
            chat_id=user.chat_id,
            credits_added=credit_package.credit_amount,
            new_balance=new_balance,
        )
    except Exception as e:
        logger.error(f"Failed to send payment notification: {e}")
    finally:
        await bot.session.close()


async def cleanup_stale_payments() -> None:
    """Check stale pending payments via YooKassa API and update their status."""
    threshold = datetime.utcnow() - timedelta(
        minutes=settings.stale_payment_threshold_minutes
    )

    async with get_session() as session:
        payment_repo = PaymentRepository(session)
        stale = await payment_repo.get_stale_pending(older_than=threshold)

        if not stale:
            return

        logger.info(f"Stale payment cleanup: found {len(stale)} pending payment(s)")

        for payment in stale:
            try:
                assert payment.yookassa_payment_id is not None
                async with _create_client() as client:
                    yookassa_payment = await client.payment.find_one(
                        payment.yookassa_payment_id
                    )
                remote_status: str = yookassa_payment.status

                if remote_status == "succeeded":
                    logger.info(
                        f"Stale payment {payment.payment_id}: "
                        f"YooKassa status=succeeded, processing missed webhook"
                    )
                    payment_data = yookassa_payment.model_dump()
                    await _handle_payment_succeeded(
                        session, payment_repo, payment, payment_data
                    )
                elif remote_status == "canceled":
                    logger.info(
                        f"Stale payment {payment.payment_id}: "
                        f"YooKassa status=canceled, marking failed"
                    )
                    await payment_repo.mark_failed(
                        payment, {"reason": "canceled_in_yookassa"}
                    )
                elif remote_status == "pending":
                    logger.info(
                        f"Stale payment {payment.payment_id}: "
                        f"YooKassa status=pending, canceling abandoned payment"
                    )
                    async with _create_client() as client:
                        await client.payment.cancel(payment.yookassa_payment_id)
                    await payment_repo.mark_failed(
                        payment, {"reason": "canceled_stale_pending"}
                    )
                else:
                    logger.warning(
                        f"Stale payment {payment.payment_id}: "
                        f"unexpected YooKassa status={remote_status}"
                    )
            except Exception:
                logger.exception(
                    f"Stale payment cleanup error for payment {payment.payment_id}"
                )


async def stale_payment_cleanup_loop() -> None:
    """Background loop that periodically cleans up stale pending payments."""
    interval = settings.stale_payment_check_interval_seconds
    threshold = settings.stale_payment_threshold_minutes
    logger.info(
        f"Stale payment cleanup loop started "
        f"(interval={interval}s, threshold={threshold}min)"
    )
    try:
        while True:
            await asyncio.sleep(interval)
            try:
                await cleanup_stale_payments()
            except Exception:
                logger.exception("Stale payment cleanup loop iteration failed")
    except asyncio.CancelledError:
        logger.info("Stale payment cleanup loop stopped")
        raise
