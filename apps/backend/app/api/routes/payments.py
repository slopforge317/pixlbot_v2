"""Telegram Payments endpoints for the Mini App."""

from aiogram import Bot
from api.deps import CurrentUser, DBSession
from api.schemas.payment import (
    CreatePaymentRequest,
    CreatePaymentResponse,
    PaymentStatusResponse,
)
from db.models.credit_package import CreditPackage
from db.repositories.payment import PaymentRepository
from fastapi import APIRouter, HTTPException, Request
from services.payment import (
    PaymentConfigurationError,
    PaymentInvoiceError,
    send_package_invoice,
)

router = APIRouter(prefix="/api", tags=["payments"])


@router.post("/payments", response_model=CreatePaymentResponse)
async def create_payment(
    body: CreatePaymentRequest,
    user: CurrentUser,
    session: DBSession,
    request: Request,
) -> CreatePaymentResponse:
    """Send a YooKassa-backed Telegram invoice to the current user's chat."""
    package = await session.get(CreditPackage, body.credit_package_id)
    if not package or not package.is_active:
        raise HTTPException(status_code=404, detail="Credit package not found")

    bot = getattr(request.app.state, "bot", None)
    if not isinstance(bot, Bot):
        raise HTTPException(status_code=503, detail="Telegram bot is not available")

    try:
        invoice = await send_package_invoice(
            bot=bot,
            session=session,
            user=user,
            package=package,
        )
    except PaymentConfigurationError as exc:
        raise HTTPException(
            status_code=503, detail="Payments are not configured"
        ) from exc
    except PaymentInvoiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return CreatePaymentResponse(
        payment_id=invoice.payment_id,
        invoice_message_id=invoice.message_id,
    )


@router.get("/payments/{payment_id}/status", response_model=PaymentStatusResponse)
async def get_payment_status(
    payment_id: int,
    user: CurrentUser,
    session: DBSession,
) -> PaymentStatusResponse:
    """Return the local status of a payment owned by the current user."""
    payment = await PaymentRepository(session).get_by_id(payment_id)
    if not payment or payment.user_id != user.user_id:
        raise HTTPException(status_code=404, detail="Payment not found")

    return PaymentStatusResponse(
        payment_id=payment.payment_id,
        status=payment.status.value,
    )
