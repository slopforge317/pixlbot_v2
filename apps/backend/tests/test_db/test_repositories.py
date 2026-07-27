import pytest
from db.enums import JobStatus, TransactionType
from db.models import (
    AIModel,
    CreditPackage,
    GenerationJob,
    PricingVariant,
    Provider,
    Transaction,
    User,
)
from db.repositories import (
    AiModelRepository,
    CreditPackageRepository,
    GenerationJobRepository,
    PricingVariantRepository,
    ProviderRepository,
    TransactionRepository,
    UserRepository,
)
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_user_get_or_create_new(db_session: AsyncSession) -> None:
    """Test get_or_create creates new user."""
    repo = UserRepository(db_session)

    user, created = await repo.get_or_create(
        telegram_user_id=123456789,
        chat_id=123456789,
        first_name="New",
        last_name="User",
        username="newuser",
    )

    assert created is True
    assert user.user_id is not None
    assert user.telegram_user_id == 123456789


@pytest.mark.asyncio
async def test_user_get_or_create_existing(db_session: AsyncSession) -> None:
    """Test get_or_create returns existing user."""
    repo = UserRepository(db_session)

    # Create first
    user1, created1 = await repo.get_or_create(
        telegram_user_id=111222333,
        chat_id=111222333,
        first_name="Existing",
    )
    assert created1 is True

    # Get existing
    user2, created2 = await repo.get_or_create(
        telegram_user_id=111222333,
        chat_id=111222333,
        first_name="Different",
    )
    assert created2 is False
    assert user2.user_id == user1.user_id
    assert user2.first_name == "Existing"  # Original name preserved


@pytest.mark.asyncio
async def test_user_get_by_telegram_id(db_session: AsyncSession) -> None:
    """Test get_by_telegram_id."""
    repo = UserRepository(db_session)

    # Create user
    user = User(
        telegram_user_id=444555666,
        first_name="Find",
        chat_id=444555666,
    )
    db_session.add(user)
    await db_session.flush()

    # Find by telegram_id
    found = await repo.get_by_telegram_id(444555666)
    assert found is not None
    assert found.user_id == user.user_id

    # Not found
    not_found = await repo.get_by_telegram_id(999999999)
    assert not_found is None


@pytest.mark.asyncio
async def test_user_balance(db_session: AsyncSession) -> None:
    """Test balance calculation from transactions."""
    repo = UserRepository(db_session)

    # Create user
    user = User(
        telegram_user_id=777888999,
        first_name="Balanced",
        chat_id=777888999,
    )
    db_session.add(user)
    await db_session.flush()

    # Initial balance is 0
    balance = await repo.get_balance(user.user_id)
    assert balance == 0

    # Add deposit
    tx1 = Transaction(
        user_id=user.user_id,
        type=TransactionType.deposit,
        amount_credits=100,
    )
    db_session.add(tx1)
    await db_session.flush()

    balance = await repo.get_balance(user.user_id)
    assert balance == 100

    # Add withdrawal
    tx2 = Transaction(
        user_id=user.user_id,
        type=TransactionType.withdrawal,
        amount_credits=-30,
    )
    db_session.add(tx2)
    await db_session.flush()

    balance = await repo.get_balance(user.user_id)
    assert balance == 70

    # Add refund
    tx3 = Transaction(
        user_id=user.user_id,
        type=TransactionType.refund,
        amount_credits=10,
    )
    db_session.add(tx3)
    await db_session.flush()

    balance = await repo.get_balance(user.user_id)
    assert balance == 80


# Helper to create provider + model + pricing variant
async def _create_test_hierarchy(
    db_session: AsyncSession,
    provider_title: str = "TestProvider",
    gen_type: str = "image",
    api_model_id: str = "test/text-to-image",
    model_title: str = "Text-to-Image",
    variant_values: dict | None = None,
    price: int = 10,
    pv_active: bool = True,
) -> tuple[Provider, AIModel, PricingVariant]:
    """Create a provider → model → pricing_variant chain."""
    provider = Provider(title=provider_title, gen_type=gen_type, active=True)
    db_session.add(provider)
    await db_session.flush()

    model = AIModel(
        provider_id=provider.id,
        api_model_id=api_model_id,
        title=model_title,
        input_schema={},
        variant_keys=[],
        active=True,
    )
    db_session.add(model)
    await db_session.flush()

    pv = PricingVariant(
        model_id=model.id,
        variant_values=variant_values or {},
        price=price,
        active=pv_active,
    )
    db_session.add(pv)
    await db_session.flush()

    return provider, model, pv


@pytest.mark.asyncio
async def test_generation_job_get_user_jobs(db_session: AsyncSession) -> None:
    """Test getting user's generation jobs."""
    # Setup
    user = User(
        telegram_user_id=111000111,
        first_name="JobUser",
        chat_id=111000111,
    )
    db_session.add(user)
    await db_session.flush()

    _, _, pv = await _create_test_hierarchy(db_session)

    # Create jobs
    for i in range(3):
        job = GenerationJob(
            user_id=user.user_id,
            pricing_variant_id=pv.id,
            status=JobStatus.done,
            cost_credit=10,
            prompt=f"Prompt {i}",
            generation_params={},
        )
        db_session.add(job)
    await db_session.flush()

    # Get jobs
    repo = GenerationJobRepository(db_session)
    jobs = await repo.get_user_jobs(user.user_id, limit=10)

    assert len(jobs) == 3


@pytest.mark.asyncio
async def test_generation_job_get_pending(db_session: AsyncSession) -> None:
    """Test getting pending jobs for polling."""
    # Setup
    user = User(
        telegram_user_id=222000222,
        first_name="PendingUser",
        chat_id=222000222,
    )
    db_session.add(user)
    await db_session.flush()

    _, _, pv = await _create_test_hierarchy(
        db_session, provider_title="TestProvider2", api_model_id="test/img2"
    )

    # Create jobs with different statuses
    for status in [
        JobStatus.queue,
        JobStatus.processing,
        JobStatus.done,
        JobStatus.error,
    ]:
        job = GenerationJob(
            user_id=user.user_id,
            pricing_variant_id=pv.id,
            status=status,
            cost_credit=10,
            prompt=f"Prompt {status.value}",
            generation_params={},
        )
        db_session.add(job)
    await db_session.flush()

    # Get pending (queue + processing)
    repo = GenerationJobRepository(db_session)
    pending = await repo.get_pending_jobs()

    assert len(pending) == 2
    statuses = {j.status for j in pending}
    assert statuses == {JobStatus.queue, JobStatus.processing}


# =============================================================================
# ProviderRepository Tests
# =============================================================================


@pytest.mark.asyncio
async def test_provider_get_all_active_with_models(
    db_session: AsyncSession,
) -> None:
    """Test getting all active providers with models and pricing."""
    provider1 = Provider(title="ImageProvider", gen_type="image", active=True)
    provider2 = Provider(title="VideoProvider", gen_type="video", active=True)
    provider_inactive = Provider(
        title="InactiveProvider", gen_type="image", active=False
    )
    db_session.add_all([provider1, provider2, provider_inactive])
    await db_session.flush()

    model1 = AIModel(
        provider_id=provider1.id,
        api_model_id="img/model1",
        title="Image Model",
        input_schema={},
        variant_keys=[],
        active=True,
    )
    db_session.add(model1)
    await db_session.flush()

    pv1 = PricingVariant(model_id=model1.id, variant_values={}, price=10, active=True)
    db_session.add(pv1)
    await db_session.flush()

    repo = ProviderRepository(db_session)
    providers = await repo.get_all_active_with_models()

    # Should not include inactive provider
    assert len(providers) == 2
    titles = {p.title for p in providers}
    assert "InactiveProvider" not in titles


@pytest.mark.asyncio
async def test_provider_get_by_gen_type(db_session: AsyncSession) -> None:
    """Test filtering providers by gen_type."""
    provider_img = Provider(title="ImageProvider", gen_type="image", active=True)
    provider_vid = Provider(title="VideoProvider", gen_type="video", active=True)
    db_session.add_all([provider_img, provider_vid])
    await db_session.flush()

    repo = ProviderRepository(db_session)

    image_providers = await repo.get_by_gen_type("image")
    assert len(image_providers) == 1
    assert image_providers[0].title == "ImageProvider"

    video_providers = await repo.get_by_gen_type("video")
    assert len(video_providers) == 1
    assert video_providers[0].title == "VideoProvider"


# =============================================================================
# AiModelRepository Tests
# =============================================================================


@pytest.mark.asyncio
async def test_ai_model_get_by_api_model_id(db_session: AsyncSession) -> None:
    """Test getting model by API model ID."""
    provider = Provider(title="TestProvider", gen_type="image", active=True)
    db_session.add(provider)
    await db_session.flush()

    model = AIModel(
        provider_id=provider.id,
        api_model_id="test/unique-model",
        title="Unique Model",
        input_schema={},
        variant_keys=[],
        active=True,
    )
    db_session.add(model)
    await db_session.flush()

    repo = AiModelRepository(db_session)

    found = await repo.get_by_api_model_id("test/unique-model")
    assert found is not None
    assert found.title == "Unique Model"

    not_found = await repo.get_by_api_model_id("nonexistent")
    assert not_found is None


@pytest.mark.asyncio
async def test_ai_model_get_with_variants(db_session: AsyncSession) -> None:
    """Test getting model with active pricing variants."""
    provider = Provider(title="TestProvider", gen_type="image", active=True)
    db_session.add(provider)
    await db_session.flush()

    model = AIModel(
        provider_id=provider.id,
        api_model_id="test/model",
        title="Test Model",
        input_schema={},
        variant_keys=["quality"],
        active=True,
    )
    db_session.add(model)
    await db_session.flush()

    pv_active = PricingVariant(
        model_id=model.id,
        variant_values={"quality": "high"},
        price=10,
        active=True,
    )
    pv_inactive = PricingVariant(
        model_id=model.id,
        variant_values={"quality": "low"},
        price=5,
        active=False,
    )
    db_session.add_all([pv_active, pv_inactive])
    await db_session.flush()

    repo = AiModelRepository(db_session)
    result = await repo.get_with_variants(model.id)

    assert result is not None
    assert result.title == "Test Model"
    # Only active variants
    assert len(result.pricing_variants) == 1
    assert result.pricing_variants[0].variant_values == {"quality": "high"}


# =============================================================================
# PricingVariantRepository Tests
# =============================================================================


@pytest.mark.asyncio
async def test_pricing_variant_get_by_id_with_model(
    db_session: AsyncSession,
) -> None:
    """Test getting pricing variant with eager-loaded model and provider."""
    provider, model, pv = await _create_test_hierarchy(
        db_session,
        provider_title="PVProvider",
        api_model_id="pv/test",
    )

    repo = PricingVariantRepository(db_session)
    result = await repo.get_by_id_with_model(pv.id)

    assert result is not None
    assert result.model is not None
    assert result.model.api_model_id == "pv/test"
    assert result.model.provider is not None
    assert result.model.provider.title == "PVProvider"


@pytest.mark.asyncio
async def test_pricing_variant_get_active_by_model_id(
    db_session: AsyncSession,
) -> None:
    """Test getting active pricing variants for a model."""
    provider = Provider(title="TestProvider", gen_type="image", active=True)
    db_session.add(provider)
    await db_session.flush()

    model = AIModel(
        provider_id=provider.id,
        api_model_id="test/model-pv",
        title="Test",
        input_schema={},
        variant_keys=[],
        active=True,
    )
    db_session.add(model)
    await db_session.flush()

    active_pv = PricingVariant(
        model_id=model.id, variant_values={}, price=10, active=True
    )
    inactive_pv = PricingVariant(
        model_id=model.id, variant_values={}, price=20, active=False
    )
    db_session.add_all([active_pv, inactive_pv])
    await db_session.flush()

    repo = PricingVariantRepository(db_session)
    variants = await repo.get_active_by_model_id(model.id)

    assert len(variants) == 1
    assert variants[0].price == 10


# =============================================================================
# CreditPackageRepository Tests
# =============================================================================


@pytest.mark.asyncio
async def test_credit_package_get_active(db_session: AsyncSession) -> None:
    """Test getting only active packages."""
    active_pkg = CreditPackage(
        name="Active Package",
        description="Active",
        credit_amount=100,
        fiat_price=9900,
        is_active=True,
    )
    inactive_pkg = CreditPackage(
        name="Inactive Package",
        description="Inactive",
        credit_amount=200,
        fiat_price=19900,
        is_active=False,
    )
    db_session.add_all([active_pkg, inactive_pkg])
    await db_session.flush()

    repo = CreditPackageRepository(db_session)
    packages = await repo.get_active()

    assert len(packages) == 1
    assert packages[0].name == "Active Package"


@pytest.mark.asyncio
async def test_credit_package_get_active_ordered_by_price(
    db_session: AsyncSession,
) -> None:
    """Test getting active packages ordered by price."""
    pkg_expensive = CreditPackage(
        name="Expensive",
        description="Expensive",
        credit_amount=500,
        fiat_price=49900,
        is_active=True,
    )
    pkg_cheap = CreditPackage(
        name="Cheap",
        description="Cheap",
        credit_amount=100,
        fiat_price=9900,
        is_active=True,
    )
    pkg_medium = CreditPackage(
        name="Medium",
        description="Medium",
        credit_amount=250,
        fiat_price=24900,
        is_active=True,
    )
    pkg_inactive = CreditPackage(
        name="Inactive",
        description="Inactive",
        credit_amount=1000,
        fiat_price=5000,
        is_active=False,
    )
    db_session.add_all([pkg_expensive, pkg_cheap, pkg_medium, pkg_inactive])
    await db_session.flush()

    repo = CreditPackageRepository(db_session)
    packages = await repo.get_active_ordered_by_price()

    assert len(packages) == 3
    assert packages[0].name == "Cheap"
    assert packages[1].name == "Medium"
    assert packages[2].name == "Expensive"


# =============================================================================
# TransactionRepository Tests
# =============================================================================


@pytest.mark.asyncio
async def test_transaction_get_user_transactions(db_session: AsyncSession) -> None:
    """Test getting user's transaction history."""
    user = User(
        telegram_user_id=333444555,
        first_name="TxUser",
        chat_id=333444555,
    )
    db_session.add(user)
    await db_session.flush()

    # Create multiple transactions
    for i in range(5):
        tx = Transaction(
            user_id=user.user_id,
            type=TransactionType.deposit,
            amount_credits=100 * (i + 1),
        )
        db_session.add(tx)
    await db_session.flush()

    repo = TransactionRepository(db_session)

    # Get all
    all_txs = await repo.get_user_transactions(user.user_id)
    assert len(all_txs) == 5

    # Test pagination
    limited = await repo.get_user_transactions(user.user_id, limit=2)
    assert len(limited) == 2


@pytest.mark.asyncio
async def test_transaction_get_by_type(db_session: AsyncSession) -> None:
    """Test filtering transactions by type."""
    user = User(
        telegram_user_id=444555666,
        first_name="TypeUser",
        chat_id=444555666,
    )
    db_session.add(user)
    await db_session.flush()

    # Create transactions of different types
    deposit = Transaction(
        user_id=user.user_id,
        type=TransactionType.deposit,
        amount_credits=100,
    )
    withdrawal = Transaction(
        user_id=user.user_id,
        type=TransactionType.withdrawal,
        amount_credits=-50,
    )
    refund = Transaction(
        user_id=user.user_id,
        type=TransactionType.refund,
        amount_credits=20,
    )
    db_session.add_all([deposit, withdrawal, refund])
    await db_session.flush()

    repo = TransactionRepository(db_session)

    deposits = await repo.get_by_type(user.user_id, TransactionType.deposit)
    assert len(deposits) == 1
    assert deposits[0].amount_credits == 100

    withdrawals = await repo.get_by_type(user.user_id, TransactionType.withdrawal)
    assert len(withdrawals) == 1
    assert withdrawals[0].amount_credits == -50


@pytest.mark.asyncio
async def test_transaction_create_deposit(db_session: AsyncSession) -> None:
    """Test creating deposit transaction."""
    user = User(
        telegram_user_id=555666777,
        first_name="DepositUser",
        chat_id=555666777,
    )
    db_session.add(user)
    await db_session.flush()

    repo = TransactionRepository(db_session)
    tx = await repo.create_deposit(
        user_id=user.user_id,
        amount_credits=100,
        payment_id=None,
        credit_package_id=None,
    )

    assert tx.tx_id is not None
    assert tx.type == TransactionType.deposit
    assert tx.amount_credits == 100


@pytest.mark.asyncio
async def test_transaction_create_withdrawal(db_session: AsyncSession) -> None:
    """Test creating withdrawal transaction (should be negative)."""
    user = User(
        telegram_user_id=666777888,
        first_name="WithdrawUser",
        chat_id=666777888,
    )
    db_session.add(user)
    await db_session.flush()

    # Create a dummy job for FK
    _, _, pv = await _create_test_hierarchy(
        db_session,
        provider_title="WithdrawProvider",
        api_model_id="withdraw/test",
    )

    job = GenerationJob(
        user_id=user.user_id,
        pricing_variant_id=pv.id,
        status=JobStatus.done,
        cost_credit=10,
        prompt="Test",
        generation_params={},
    )
    db_session.add(job)
    await db_session.flush()

    repo = TransactionRepository(db_session)
    tx = await repo.create_withdrawal(
        user_id=user.user_id,
        amount_credits=50,
        job_id=job.job_id,
    )

    assert tx.tx_id is not None
    assert tx.type == TransactionType.withdrawal
    assert tx.amount_credits == -50  # Should be negative
    assert tx.job_id == job.job_id


@pytest.mark.asyncio
async def test_transaction_create_refund(db_session: AsyncSession) -> None:
    """Test creating refund transaction (should be positive)."""
    user = User(
        telegram_user_id=777888999,
        first_name="RefundUser",
        chat_id=777888999,
    )
    db_session.add(user)
    await db_session.flush()

    # Create a dummy job for FK
    _, _, pv = await _create_test_hierarchy(
        db_session,
        provider_title="RefundProvider",
        api_model_id="refund/test",
    )

    job = GenerationJob(
        user_id=user.user_id,
        pricing_variant_id=pv.id,
        status=JobStatus.error,
        cost_credit=10,
        prompt="Test",
        generation_params={},
    )
    db_session.add(job)
    await db_session.flush()

    repo = TransactionRepository(db_session)
    tx = await repo.create_refund(
        user_id=user.user_id,
        amount_credits=30,
        job_id=job.job_id,
    )

    assert tx.tx_id is not None
    assert tx.type == TransactionType.refund
    assert tx.amount_credits == 30  # Should be positive
    assert tx.job_id == job.job_id
