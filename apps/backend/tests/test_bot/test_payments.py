import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.types import Message, PreCheckoutQuery
from db.enums import PaymentStatus
from db.models.credit_package import CreditPackage
from db.models.payment import Payment
from db.models.user import User
from db.repositories.payment import PaymentRepository
from db.repositories.transaction import TransactionRepository
from db.repositories.user import UserRepository
from services.payment import PaymentInvoiceError, send_package_invoice
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.handlers import payments as payment_handlers


async def _create_user_and_package(
    session: AsyncSession,
) -> tuple[User, CreditPackage]:
    user = User(
        telegram_user_id=987654321,
        chat_id=987654321,
        first_name="Payment",
    )
    package = CreditPackage(
        name="Старт",
        description="100 кредитов",
        credit_amount=100,
        fiat_price=19900,
        is_active=True,
    )
    session.add_all([user, package])
    await session.flush()
    return user, package


@pytest.mark.asyncio
async def test_send_package_invoice_requests_email_and_receipt(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user, package = await _create_user_and_package(db_session)
    bot = MagicMock()
    bot.send_invoice = AsyncMock(return_value=MagicMock(message_id=321))
    monkeypatch.setattr(
        "services.payment.settings.yookassa_provider_token",
        "381764678:TEST:provider-token",
    )

    sent = await send_package_invoice(
        bot=bot,
        session=db_session,
        user=user,
        package=package,
    )

    assert sent.message_id == 321
    payment = await db_session.get(Payment, sent.payment_id)
    assert payment is not None
    assert payment.status == PaymentStatus.pending
    assert payment.credits_amount == 100
    assert payment.amount_currency == 19900

    kwargs = bot.send_invoice.await_args.kwargs
    assert kwargs["need_email"] is True
    assert kwargs["send_email_to_provider"] is True
    assert kwargs["currency"] == "RUB"
    assert kwargs["prices"][0].amount == 19900
    receipt = json.loads(kwargs["provider_data"])["receipt"]
    assert receipt["items"][0]["amount"] == {
        "value": "199.00",
        "currency": "RUB",
    }
    assert receipt["items"][0]["payment_subject"] == "service"


@pytest.mark.asyncio
async def test_send_package_invoice_marks_payment_failed_on_telegram_error(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user, package = await _create_user_and_package(db_session)
    bot = MagicMock()
    bot.send_invoice = AsyncMock(side_effect=RuntimeError("Telegram unavailable"))
    monkeypatch.setattr(
        "services.payment.settings.yookassa_provider_token",
        "381764678:TEST:provider-token",
    )

    with pytest.raises(PaymentInvoiceError):
        await send_package_invoice(
            bot=bot,
            session=db_session,
            user=user,
            package=package,
        )

    payment = await PaymentRepository(db_session).get_by_invoice_payload(
        bot.send_invoice.await_args.kwargs["payload"]
    )
    assert payment is not None
    assert payment.status == PaymentStatus.failed


@pytest.mark.asyncio
async def test_pre_checkout_rejects_missing_email(
    db_session: AsyncSession,
) -> None:
    user, package = await _create_user_and_package(db_session)
    payment = await PaymentRepository(db_session).create_pending(
        user_id=user.user_id,
        amount_currency=package.fiat_price,
        credit_package_id=package.id,
        credits_amount=package.credit_amount,
        invoice_payload="missing-email-payload",
    )
    await db_session.commit()

    query = MagicMock(spec=PreCheckoutQuery)
    query.invoice_payload = payment.invoice_payload
    query.currency = "RUB"
    query.total_amount = package.fiat_price
    query.from_user = MagicMock(id=user.telegram_user_id)
    query.order_info = MagicMock(email=None)
    query.answer = AsyncMock()

    await payment_handlers.on_pre_checkout(query, db_session)

    query.answer.assert_awaited_once_with(
        ok=False,
        error_message="Укажите email для получения чека.",
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("payload", "telegram_user_id", "amount"),
    [
        ("unknown-payload", 987654321, 19900),
        ("validated-payload", 111111111, 19900),
        ("validated-payload", 987654321, 9900),
    ],
)
async def test_pre_checkout_rejects_invalid_invoice_data(
    db_session: AsyncSession,
    payload: str,
    telegram_user_id: int,
    amount: int,
) -> None:
    user, package = await _create_user_and_package(db_session)
    await PaymentRepository(db_session).create_pending(
        user_id=user.user_id,
        amount_currency=package.fiat_price,
        credit_package_id=package.id,
        credits_amount=package.credit_amount,
        invoice_payload="validated-payload",
    )
    await db_session.commit()

    query = MagicMock(spec=PreCheckoutQuery)
    query.invoice_payload = payload
    query.currency = "RUB"
    query.total_amount = amount
    query.from_user = MagicMock(id=telegram_user_id)
    query.order_info = MagicMock(email="buyer@example.com")
    query.answer = AsyncMock()

    await payment_handlers.on_pre_checkout(query, db_session)

    query.answer.assert_awaited_once_with(
        ok=False,
        error_message=payment_handlers.PAYMENT_INVALID,
    )


@pytest.mark.asyncio
async def test_pre_checkout_accepts_valid_invoice(
    db_session: AsyncSession,
) -> None:
    user, package = await _create_user_and_package(db_session)
    payment = await PaymentRepository(db_session).create_pending(
        user_id=user.user_id,
        amount_currency=package.fiat_price,
        credit_package_id=package.id,
        credits_amount=package.credit_amount,
        invoice_payload="valid-payload",
    )
    await db_session.commit()

    query = MagicMock(spec=PreCheckoutQuery)
    query.invoice_payload = payment.invoice_payload
    query.currency = "RUB"
    query.total_amount = package.fiat_price
    query.from_user = MagicMock(id=user.telegram_user_id)
    query.order_info = MagicMock(email="buyer@example.com")
    query.answer = AsyncMock()

    await payment_handlers.on_pre_checkout(query, db_session)

    query.answer.assert_awaited_once_with(ok=True)


@pytest.mark.asyncio
async def test_successful_payment_grants_credits_only_once(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user, package = await _create_user_and_package(db_session)
    payment = await PaymentRepository(db_session).create_pending(
        user_id=user.user_id,
        amount_currency=package.fiat_price,
        credit_package_id=package.id,
        credits_amount=package.credit_amount,
        invoice_payload="successful-payment-payload",
    )
    await db_session.commit()

    successful = MagicMock(
        invoice_payload=payment.invoice_payload,
        currency="RUB",
        total_amount=package.fiat_price,
        telegram_payment_charge_id="telegram-charge-1",
        provider_payment_charge_id="yookassa-charge-1",
        order_info=MagicMock(email="buyer@example.com"),
    )
    message = MagicMock(spec=Message)
    message.successful_payment = successful
    message.from_user = MagicMock(id=user.telegram_user_id)
    message.answer = AsyncMock()
    notify = AsyncMock()
    monkeypatch.setattr(payment_handlers, "send_payment_success", notify)

    await payment_handlers.on_successful_payment(message, db_session, MagicMock())
    await payment_handlers.on_successful_payment(message, db_session, MagicMock())

    await db_session.refresh(payment)
    assert payment.status == PaymentStatus.success
    assert payment.customer_email == "buyer@example.com"
    assert payment.provider_payment_charge_id == "yookassa-charge-1"
    deposit = await TransactionRepository(db_session).get_by_payment_id(
        payment.payment_id
    )
    assert deposit is not None
    assert deposit.amount_credits == package.credit_amount
    assert await UserRepository(db_session).get_balance(user.user_id) == 100
    notify.assert_awaited_once()
