"""Payment API endpoints."""

from api.deps import CurrentUser, DBSession
from api.schemas.payment import (
    CreatePaymentRequest,
    CreatePaymentResponse,
    PaymentStatusResponse,
)
from core.config import settings
from db.models.credit_package import CreditPackage
from db.repositories.payment import PaymentRepository
from fastapi import APIRouter, HTTPException
from loguru import logger
from services.payment import create_yookassa_payment

router = APIRouter(prefix="/api", tags=["payments"])


@router.post("/payments", response_model=CreatePaymentResponse)
async def create_payment(
    body: CreatePaymentRequest,
    user: CurrentUser,
    session: DBSession,
) -> CreatePaymentResponse:
    """Create a payment for a credit package.

    1. Validates the credit package exists and is active
    2. Creates a pending Payment record
    3. Creates a YooKassa payment
    4. Returns the confirmation URL for redirect
    """
    # Validate credit package
    credit_package = await session.get(CreditPackage, body.credit_package_id)
    if not credit_package or not credit_package.is_active:
        raise HTTPException(status_code=404, detail="Credit package not found")

    if not settings.yookassa_shop_id:
        raise HTTPException(status_code=503, detail="Payments are not configured")

    # Create pending payment in DB
    payment_repo = PaymentRepository(session)
    payment = await payment_repo.create_pending(
        user_id=user.user_id,
        amount_currency=credit_package.fiat_price,
        credit_package_id=credit_package.id,
    )

    logger.info(
        f"Payment created: payment_id={payment.payment_id}, "
        f"user_id={user.user_id}, package_id={credit_package.id}"
    )

    # Create YooKassa payment
    try:
        # Build return URL with payment_id for status checking
        separator = "&" if "?" in settings.yookassa_return_url else "?"
        return_url = (
            f"{settings.yookassa_return_url}{separator}payment_id={payment.payment_id}"
        )

        yookassa_id, confirmation_url = await create_yookassa_payment(
            amount_kopeks=credit_package.fiat_price,
            description=f"Пополнение баланса: {credit_package.name}",
            return_url=return_url,
            metadata={"payment_id": str(payment.payment_id)},
            email=body.email,
            idempotency_key=str(payment.payment_id),
        )
    except Exception as e:
        logger.error(f"YooKassa payment creation failed: {e}")
        raise HTTPException(status_code=502, detail="Payment service unavailable")

    # Update payment with YooKassa ID
    await payment_repo.update(payment, yookassa_payment_id=yookassa_id)

    logger.info(
        f"YooKassa payment linked: payment_id={payment.payment_id}, "
        f"yookassa_id={yookassa_id}"
    )

    return CreatePaymentResponse(
        payment_id=payment.payment_id,
        confirmation_url=confirmation_url,
    )


@router.get("/payments/{payment_id}/status", response_model=PaymentStatusResponse)
async def get_payment_status(
    payment_id: int,
    user: CurrentUser,
    session: DBSession,
) -> PaymentStatusResponse:
    """Check payment status. Only the payment owner can check."""
    payment_repo = PaymentRepository(session)
    payment = await payment_repo.get_by_id(payment_id)
    if not payment or payment.user_id != user.user_id:
        raise HTTPException(status_code=404, detail="Payment not found")

    return PaymentStatusResponse(
        payment_id=payment.payment_id,
        status=payment.status.value,
    )
