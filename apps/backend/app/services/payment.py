"""Telegram Payments invoice service backed by YooKassa."""

import json
import secrets
from dataclasses import dataclass
from typing import Any

from aiogram import Bot
from aiogram.types import LabeledPrice, Message
from core.config import settings
from db.enums import PaymentStatus
from db.models.credit_package import CreditPackage
from db.models.user import User
from db.repositories.payment import PaymentRepository
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession


class PaymentConfigurationError(RuntimeError):
    """Telegram Payments is not configured on the server."""


class PaymentInvoiceError(RuntimeError):
    """An invoice could not be created or sent."""


@dataclass(frozen=True)
class SentInvoice:
    """Identifiers returned after an invoice is persisted and sent."""

    payment_id: int
    message_id: int


def _format_rubles(kopeks: int) -> str:
    return f"{kopeks / 100:.2f}"


def build_receipt_provider_data(
    *,
    description: str,
    amount_kopeks: int,
) -> str:
    """Build YooKassa receipt data shared by Telegram with the provider."""
    receipt: dict[str, Any] = {
        "receipt": {
            "items": [
                {
                    "description": description[:128],
                    "quantity": "1.00",
                    "amount": {
                        "value": _format_rubles(amount_kopeks),
                        "currency": "RUB",
                    },
                    "vat_code": settings.yookassa_vat_code,
                    "payment_mode": settings.yookassa_payment_mode,
                    "payment_subject": settings.yookassa_payment_subject,
                }
            ],
            "tax_system_code": settings.yookassa_tax_system_code,
        }
    }
    return json.dumps(receipt, ensure_ascii=False, separators=(",", ":"))


def _build_invoice_description(package: CreditPackage) -> str:
    description = (
        package.description or f"Пополнение на {package.credit_amount} кредитов"
    )
    return description.strip()[:255]


async def send_package_invoice(
    *,
    bot: Bot,
    session: AsyncSession,
    user: User,
    package: CreditPackage,
) -> SentInvoice:
    """Persist and send a Telegram invoice for an active credit package."""
    if not settings.yookassa_provider_token:
        raise PaymentConfigurationError("YOOKASSA_PROVIDER_TOKEN is not configured")
    if not package.is_active:
        raise PaymentInvoiceError("Credit package is not active")

    invoice_payload = secrets.token_urlsafe(32)
    payment_repo = PaymentRepository(session)
    payment = await payment_repo.create_pending(
        user_id=user.user_id,
        amount_currency=package.fiat_price,
        credits_amount=package.credit_amount,
        credit_package_id=package.id,
        invoice_payload=invoice_payload,
    )

    # Persist before contacting Telegram so pre-checkout can resolve the payload.
    await session.commit()

    receipt_description = f"Пополнение баланса PixlBot: {package.name}"
    try:
        invoice_message: Message = await bot.send_invoice(
            chat_id=user.chat_id,
            title=package.name[:32],
            description=_build_invoice_description(package),
            payload=invoice_payload,
            provider_token=settings.yookassa_provider_token,
            currency="RUB",
            prices=[
                LabeledPrice(
                    label=receipt_description[:32],
                    amount=package.fiat_price,
                )
            ],
            need_email=True,
            send_email_to_provider=True,
            provider_data=build_receipt_provider_data(
                description=receipt_description,
                amount_kopeks=package.fiat_price,
            ),
            start_parameter=f"payment-{payment.payment_id}",
        )
    except Exception as exc:
        logger.exception(
            f"Telegram invoice send failed: payment_id={payment.payment_id}, "
            f"user_id={user.user_id}"
        )
        payment.status = PaymentStatus.failed
        payment.details = {"reason": "telegram_invoice_send_failed"}
        await session.commit()
        raise PaymentInvoiceError("Не удалось отправить счёт в Telegram") from exc

    logger.info(
        f"Telegram invoice sent: payment_id={payment.payment_id}, "
        f"user_id={user.user_id}, message_id={invoice_message.message_id}"
    )
    return SentInvoice(
        payment_id=payment.payment_id,
        message_id=invoice_message.message_id,
    )
