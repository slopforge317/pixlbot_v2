"""Payment API schemas."""

from pydantic import BaseModel


class CreatePaymentRequest(BaseModel):
    """Request to create a payment for a credit package."""

    credit_package_id: int


class CreatePaymentResponse(BaseModel):
    """Response with payment info and YooKassa redirect URL."""

    payment_id: int
    invoice_message_id: int


class PaymentStatusResponse(BaseModel):
    """Response with payment status."""

    payment_id: int
    status: str  # pending | success | failed
