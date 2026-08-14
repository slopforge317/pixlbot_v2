"""Telegram Payments handlers for YooKassa invoices."""

from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery, Message, PreCheckoutQuery
from db.enums import PaymentStatus
from db.models.credit_package import CreditPackage
from db.repositories.payment import PaymentRepository
from db.repositories.transaction import TransactionRepository
from db.repositories.user import UserRepository
from loguru import logger
from services.notification import send_payment_success
from services.payment import (
    PaymentConfigurationError,
    PaymentInvoiceError,
    send_package_invoice,
)
from sqlalchemy.ext.asyncio import AsyncSession

router = Router(name="payments")

PAYMENT_UNAVAILABLE = "Оплата временно недоступна. Попробуйте немного позже."
PAYMENT_INVALID = "Счёт устарел или изменился. Выберите пакет ещё раз."


def _pre_checkout_error(
    query: PreCheckoutQuery,
    *,
    payment_status: PaymentStatus | None,
    payment_user_telegram_id: int | None,
    amount_currency: int | None,
    currency: str | None,
) -> str | None:
    email = query.order_info.email if query.order_info else None
    if payment_status != PaymentStatus.pending:
        return PAYMENT_INVALID
    if payment_user_telegram_id != query.from_user.id:
        return PAYMENT_INVALID
    if query.currency != currency or query.total_amount != amount_currency:
        return PAYMENT_INVALID
    if not email:
        return "Укажите email для получения чека."
    return None


@router.callback_query(F.data.startswith("payment:buy:"))
async def on_buy_package(
    callback: CallbackQuery,
    session: AsyncSession,
    bot: Bot,
) -> None:
    """Send an invoice after a package button is pressed in the bot."""
    await callback.answer()
    if not callback.from_user:
        return

    try:
        package_id = int((callback.data or "").rsplit(":", 1)[-1])
    except ValueError:
        logger.warning(f"Invalid payment callback data: {callback.data!r}")
        return

    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    package = await session.get(CreditPackage, package_id)
    if not user or not package or not package.is_active:
        await bot.send_message(callback.from_user.id, PAYMENT_INVALID)
        return

    try:
        await send_package_invoice(
            bot=bot,
            session=session,
            user=user,
            package=package,
        )
    except (PaymentConfigurationError, PaymentInvoiceError):
        await bot.send_message(callback.from_user.id, PAYMENT_UNAVAILABLE)


@router.pre_checkout_query()
async def on_pre_checkout(
    query: PreCheckoutQuery,
    session: AsyncSession,
) -> None:
    """Validate the persisted payment before YooKassa captures it."""
    try:
        payment = await PaymentRepository(session).get_by_invoice_payload(
            query.invoice_payload
        )
        user_telegram_id: int | None = None
        if payment:
            user = await UserRepository(session).get_by_id(payment.user_id)
            user_telegram_id = user.telegram_user_id if user else None

        error = _pre_checkout_error(
            query,
            payment_status=payment.status if payment else None,
            payment_user_telegram_id=user_telegram_id,
            amount_currency=payment.amount_currency if payment else None,
            currency=payment.currency if payment else None,
        )
        if error:
            logger.warning(
                f"Pre-checkout rejected: telegram_user_id={query.from_user.id}, "
                f"payload={query.invoice_payload!r}, reason={error}"
            )
            await query.answer(ok=False, error_message=error)
            return

        await query.answer(ok=True)
    except Exception:
        logger.exception(
            f"Pre-checkout validation failed: telegram_user_id={query.from_user.id}"
        )
        await query.answer(ok=False, error_message=PAYMENT_UNAVAILABLE)


@router.message(F.successful_payment)
async def on_successful_payment(
    message: Message,
    session: AsyncSession,
    bot: Bot,
) -> None:
    """Atomically record a successful payment and grant credits once."""
    successful = message.successful_payment
    if not successful or not message.from_user:
        return

    payment_repo = PaymentRepository(session)
    payment = await payment_repo.get_by_invoice_payload(
        successful.invoice_payload,
        for_update=True,
    )
    if not payment:
        logger.critical(
            f"Successful Telegram payment has no local record: "
            f"telegram_charge_id={successful.telegram_payment_charge_id}"
        )
        await message.answer(PAYMENT_UNAVAILABLE)
        return

    if payment.status == PaymentStatus.success:
        logger.info(
            f"Duplicate SuccessfulPayment skipped: payment_id={payment.payment_id}"
        )
        return

    user = await UserRepository(session).get_by_id(payment.user_id)
    email = successful.order_info.email if successful.order_info else None
    valid = (
        payment.status == PaymentStatus.pending
        and user is not None
        and user.telegram_user_id == message.from_user.id
        and successful.currency == payment.currency
        and successful.total_amount == payment.amount_currency
        and bool(email)
        and payment.credits_amount is not None
    )
    if not valid:
        logger.critical(
            f"Successful Telegram payment failed local validation: "
            f"payment_id={payment.payment_id}, "
            f"telegram_charge_id={successful.telegram_payment_charge_id}"
        )
        await message.answer(PAYMENT_UNAVAILABLE)
        return

    assert user is not None
    assert email is not None
    assert payment.credits_amount is not None

    tx_repo = TransactionRepository(session)
    existing_deposit = await tx_repo.get_by_payment_id(payment.payment_id)
    if existing_deposit:
        logger.critical(
            f"Pending payment already has a deposit: payment_id={payment.payment_id}"
        )
        return

    await payment_repo.mark_success(
        payment,
        telegram_payment_charge_id=successful.telegram_payment_charge_id,
        provider_payment_charge_id=successful.provider_payment_charge_id,
        customer_email=email,
        details={
            "currency": successful.currency,
            "total_amount": successful.total_amount,
        },
    )
    await tx_repo.create_deposit(
        user_id=payment.user_id,
        amount_credits=payment.credits_amount,
        payment_id=payment.payment_id,
        credit_package_id=payment.credit_package_id,
    )
    balance = await UserRepository(session).get_balance(payment.user_id)
    await session.commit()

    await send_payment_success(
        bot=bot,
        chat_id=user.chat_id,
        credits_added=payment.credits_amount,
        new_balance=balance,
    )
