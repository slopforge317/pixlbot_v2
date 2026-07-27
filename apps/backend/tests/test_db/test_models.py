import pytest
from db.enums import JobStatus, PaymentStatus, TransactionType
from db.models import (
    AIModel,
    CreditPackage,
    GenerationJob,
    Payment,
    PricingVariant,
    Provider,
    Transaction,
    User,
)
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_create_user(db_session: AsyncSession) -> None:
    """Test creating a user."""
    user = User(
        telegram_user_id=123456789,
        first_name="Test",
        last_name="User",
        username="testuser",
        chat_id=123456789,
        utm_source="test",
    )
    db_session.add(user)
    await db_session.flush()

    assert user.user_id is not None
    assert user.telegram_user_id == 123456789
    assert user.created_at is not None


@pytest.mark.asyncio
async def test_create_credit_package(db_session: AsyncSession) -> None:
    """Test creating a credit package."""
    package = CreditPackage(
        name="Starter",
        description="100 credits for beginners",
        credit_amount=100,
        fiat_price=9900,  # 99.00 rubles
        is_active=True,
    )
    db_session.add(package)
    await db_session.flush()

    assert package.id is not None
    assert package.credit_amount == 100


@pytest.mark.asyncio
async def test_create_provider_with_model_and_pricing(
    db_session: AsyncSession,
) -> None:
    """Test creating provider with model and pricing variants."""
    provider = Provider(
        title="Test Provider",
        gen_type="image",
        active=True,
    )
    db_session.add(provider)
    await db_session.flush()

    model = AIModel(
        provider_id=provider.id,
        api_model_id="test/text-to-image",
        title="Text-to-Image",
        input_schema={"prompt": {"type": "string", "required": True}},
        variant_keys=["quality"],
        active=True,
    )
    db_session.add(model)
    await db_session.flush()

    pv = PricingVariant(
        model_id=model.id,
        variant_values={"quality": "high"},
        price=10,
        active=True,
    )
    db_session.add(pv)
    await db_session.flush()

    assert provider.id is not None
    assert model.id is not None
    assert model.provider_id == provider.id
    assert pv.id is not None
    assert pv.model_id == model.id
    assert pv.variant_values == {"quality": "high"}


@pytest.mark.asyncio
async def test_create_payment(db_session: AsyncSession) -> None:
    """Test creating a payment."""
    user = User(
        telegram_user_id=111222333,
        first_name="Payer",
        chat_id=111222333,
    )
    db_session.add(user)
    await db_session.flush()

    payment = Payment(
        user_id=user.user_id,
        status=PaymentStatus.pending,
        amount_currency=9900,
        details={"provider": "test"},
    )
    db_session.add(payment)
    await db_session.flush()

    assert payment.payment_id is not None
    assert payment.status == PaymentStatus.pending


@pytest.mark.asyncio
async def test_create_generation_job(db_session: AsyncSession) -> None:
    """Test creating a generation job."""
    # Setup
    user = User(
        telegram_user_id=444555666,
        first_name="Generator",
        chat_id=444555666,
    )
    db_session.add(user)

    provider = Provider(title="Test Provider", gen_type="image", active=True)
    db_session.add(provider)
    await db_session.flush()

    model = AIModel(
        provider_id=provider.id,
        api_model_id="test/text-to-image",
        title="Text-to-Image",
        input_schema={},
        variant_keys=[],
        active=True,
    )
    db_session.add(model)
    await db_session.flush()

    pv = PricingVariant(
        model_id=model.id,
        variant_values={},
        price=5,
        active=True,
    )
    db_session.add(pv)
    await db_session.flush()

    # Create job
    job = GenerationJob(
        user_id=user.user_id,
        pricing_variant_id=pv.id,
        status=JobStatus.queue,
        cost_credit=5,
        prompt="A beautiful sunset",
        generation_params={"seed": 42},
    )
    db_session.add(job)
    await db_session.flush()

    assert job.job_id is not None
    assert job.status == JobStatus.queue
    assert job.prompt == "A beautiful sunset"


@pytest.mark.asyncio
async def test_create_transaction(db_session: AsyncSession) -> None:
    """Test creating a transaction."""
    user = User(
        telegram_user_id=777888999,
        first_name="Spender",
        chat_id=777888999,
    )
    db_session.add(user)
    await db_session.flush()

    # Deposit transaction
    tx = Transaction(
        user_id=user.user_id,
        type=TransactionType.deposit,
        amount_credits=100,
    )
    db_session.add(tx)
    await db_session.flush()

    assert tx.tx_id is not None
    assert tx.amount_credits == 100
    assert tx.type == TransactionType.deposit
