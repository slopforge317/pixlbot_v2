"""Tests for generation service."""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from db.base import Base
from db.enums import JobStatus, TransactionType
from db.models import AIModel, GenerationJob, PricingVariant, Provider, User
from db.repositories.generation import GenerationJobRepository
from db.repositories.transaction import TransactionRepository
from services.kie import GenerationResult, KieTaskFailedError, KieTaskTimeoutError
from services.kie.enums import KieTaskState
from services.kie.schemas import TaskStatusData
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.services.generation import (
    GenerationContext,
    _build_context,
    _execute_generation,
    _handle_error,
    _handle_timeout,
    _process_generation_impl,
    _process_kie_result_impl,
)

# Ensure callback mode is disabled for all generation tests
# (production .env may have KIE_CALLBACK_ENABLED=true)
pytestmark = pytest.mark.usefixtures("disable_kie_callback")

# PostgreSQL test database URL
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://pixlbot:pixlbot_test@localhost:5432/pixlbot_pytest",
)


@pytest.fixture
def disable_kie_callback():
    """Disable KIE callback mode for tests (use polling flow)."""
    with patch("app.services.generation.settings") as mock_settings:
        from core.config import Settings
        from core.config import settings as real_settings

        # Copy all real settings attributes
        for field in Settings.model_fields:
            setattr(mock_settings, field, getattr(real_settings, field))
        # Override callback setting
        mock_settings.kie_callback_enabled = False
        yield mock_settings


@pytest.fixture
async def db_session():
    """Create PostgreSQL database session for testing."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user."""
    user = User(
        telegram_user_id=123456789,
        chat_id=123456789,
        first_name="Test",
        last_name="User",
        username="testuser",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def test_provider(db_session: AsyncSession) -> Provider:
    """Create a test provider."""
    provider = Provider(
        title="Test Provider",
        gen_type="image",
        active=True,
    )
    db_session.add(provider)
    await db_session.commit()
    await db_session.refresh(provider)
    return provider


@pytest.fixture
async def test_model(db_session: AsyncSession, test_provider: Provider) -> AIModel:
    """Create a test AI model."""
    model = AIModel(
        provider_id=test_provider.id,
        api_model_id="seedream/4.5-edit",
        title="Seedream 4.5 Edit",
        input_schema={"prompt": {"type": "string"}},
        variant_keys=[],
        active=True,
    )
    db_session.add(model)
    await db_session.commit()
    await db_session.refresh(model)
    return model


@pytest.fixture
async def test_pricing_variant(
    db_session: AsyncSession, test_model: AIModel
) -> PricingVariant:
    """Create a test pricing variant."""
    pv = PricingVariant(
        model_id=test_model.id,
        variant_values={},
        price=10,
        active=True,
    )
    db_session.add(pv)
    await db_session.commit()
    await db_session.refresh(pv)
    return pv


@pytest.fixture
async def test_job(
    db_session: AsyncSession,
    test_user: User,
    test_pricing_variant: PricingVariant,
) -> GenerationJob:
    """Create a test generation job."""
    job = GenerationJob(
        user_id=test_user.user_id,
        pricing_variant_id=test_pricing_variant.id,
        status=JobStatus.queue,
        cost_credit=10,
        prompt="A beautiful sunset",
        generation_params={"prompt": "A beautiful sunset", "seed": 42},
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)
    return job


@pytest.fixture
def mock_bot() -> MagicMock:
    """Create a mock bot."""
    bot = MagicMock()
    bot.send_photo = AsyncMock(
        return_value=MagicMock(photo=[MagicMock(file_id="file123")])
    )
    bot.send_video = AsyncMock(
        return_value=MagicMock(video=MagicMock(file_id="file456"))
    )
    bot.send_message = AsyncMock()
    return bot


@pytest.fixture
def mock_kie_service() -> MagicMock:
    """Create a mock KIE service."""
    service = MagicMock()
    service.create_generation = AsyncMock(return_value="kie_task_123")
    service.wait_for_result = AsyncMock(
        return_value=GenerationResult(
            task_id="kie_task_123",
            model="seedream/4.5-edit",
            result_urls=["https://example.com/result.jpg"],
            cost_time_ms=5000,
        )
    )
    return service


class TestBuildContext:
    """Tests for _build_context function."""

    def test_build_context_image(
        self,
        test_job: GenerationJob,
        test_user: User,
        test_pricing_variant: PricingVariant,
        test_model: AIModel,
        test_provider: Provider,
    ) -> None:
        """Test context building for image provider."""
        test_job.user = test_user
        test_job.pricing_variant = test_pricing_variant

        ctx = _build_context(
            test_job, test_user, test_pricing_variant, test_model, test_provider
        )

        assert ctx.job == test_job
        assert ctx.user == test_user
        assert ctx.pricing_variant == test_pricing_variant
        assert ctx.model == test_model
        assert ctx.provider == test_provider
        assert ctx.api_model_id == "seedream/4.5-edit"
        assert ctx.media_type == "image"

    def test_build_context_video(
        self,
        test_job: GenerationJob,
        test_user: User,
        test_pricing_variant: PricingVariant,
        test_model: AIModel,
        test_provider: Provider,
    ) -> None:
        """Test context building for video provider."""
        test_provider.gen_type = "video"

        ctx = _build_context(
            test_job, test_user, test_pricing_variant, test_model, test_provider
        )

        assert ctx.media_type == "video"


class TestHandleError:
    """Tests for _handle_error function."""

    @pytest.mark.asyncio
    async def test_handle_error_updates_job_and_refunds(
        self,
        db_session: AsyncSession,
        test_job: GenerationJob,
        test_user: User,
        mock_bot: MagicMock,
    ) -> None:
        """Test that error handler updates job status and creates refund."""
        tx_repo = TransactionRepository(db_session)

        with patch(
            "services.generation.send_generation_error",
            new_callable=AsyncMock,
        ):
            await _handle_error(
                session=db_session,
                job=test_job,
                user=test_user,
                bot=mock_bot,
                tx_repo=tx_repo,
                error_message="Test error",
            )

        # Check job status
        assert test_job.status == JobStatus.error
        assert test_job.error == "Test error"

        # Check refund transaction was created
        transactions = await tx_repo.get_user_transactions(test_user.user_id)
        refund = next(
            (t for t in transactions if t.type == TransactionType.refund), None
        )
        assert refund is not None
        assert refund.amount_credits == 10
        assert refund.job_id == test_job.job_id


class TestHandleTimeout:
    """Tests for _handle_timeout function."""

    @pytest.mark.asyncio
    async def test_handle_timeout_updates_job_and_refunds(
        self,
        db_session: AsyncSession,
        test_job: GenerationJob,
        test_user: User,
        mock_bot: MagicMock,
    ) -> None:
        """Test that timeout handler updates job status and creates refund."""
        tx_repo = TransactionRepository(db_session)

        with patch(
            "services.generation.send_generation_timeout",
            new_callable=AsyncMock,
        ):
            await _handle_timeout(
                session=db_session,
                job=test_job,
                user=test_user,
                bot=mock_bot,
                tx_repo=tx_repo,
            )

        # Check job status
        assert test_job.status == JobStatus.error
        assert test_job.error == "Generation timed out"

        # Check refund transaction was created
        transactions = await tx_repo.get_user_transactions(test_user.user_id)
        refund = next(
            (t for t in transactions if t.type == TransactionType.refund), None
        )
        assert refund is not None
        assert refund.amount_credits == 10


class TestExecuteGeneration:
    """Tests for _execute_generation function."""

    @pytest.mark.asyncio
    async def test_execute_generation_success(
        self,
        db_session: AsyncSession,
        test_job: GenerationJob,
        test_user: User,
        test_pricing_variant: PricingVariant,
        test_model: AIModel,
        test_provider: Provider,
        mock_bot: MagicMock,
        mock_kie_service: MagicMock,
    ) -> None:
        """Test successful generation execution."""
        ctx = GenerationContext(
            job=test_job,
            user=test_user,
            pricing_variant=test_pricing_variant,
            model=test_model,
            provider=test_provider,
            api_model_id="seedream/4.5-edit",
            media_type="image",
        )

        with patch(
            "services.generation.send_generation_result",
            new_callable=AsyncMock,
            return_value="file_id_123",
        ):
            await _execute_generation(
                session=db_session,
                job=test_job,
                ctx=ctx,
                kie_service=mock_kie_service,
                bot=mock_bot,
            )

        # Check job was updated
        assert test_job.status == JobStatus.done
        assert test_job.provider_task_id == "kie_task_123"
        assert test_job.success_url_asset == "https://example.com/result.jpg"
        assert test_job.provider_complete_time is not None

    @pytest.mark.asyncio
    async def test_execute_generation_passes_input_data(
        self,
        db_session: AsyncSession,
        test_job: GenerationJob,
        test_user: User,
        test_pricing_variant: PricingVariant,
        test_model: AIModel,
        test_provider: Provider,
        mock_bot: MagicMock,
        mock_kie_service: MagicMock,
    ) -> None:
        """Test generation passes generation_params as input_data to KIE."""
        ctx = GenerationContext(
            job=test_job,
            user=test_user,
            pricing_variant=test_pricing_variant,
            model=test_model,
            provider=test_provider,
            api_model_id="seedream/4.5-edit",
            media_type="image",
        )

        with patch(
            "services.generation.send_generation_result",
            new_callable=AsyncMock,
            return_value=None,
        ):
            await _execute_generation(
                session=db_session,
                job=test_job,
                ctx=ctx,
                kie_service=mock_kie_service,
                bot=mock_bot,
            )

        # Verify input_data was passed with prompt from DB column + params
        call_kwargs = mock_kie_service.create_generation.call_args
        input_data = call_kwargs.kwargs.get("input_data")
        assert input_data is not None
        assert input_data["prompt"] == "A beautiful sunset"
        assert input_data["seed"] == 42

    @pytest.mark.asyncio
    async def test_execute_generation_kie_failure(
        self,
        db_session: AsyncSession,
        test_job: GenerationJob,
        test_user: User,
        test_pricing_variant: PricingVariant,
        test_model: AIModel,
        test_provider: Provider,
        mock_bot: MagicMock,
        mock_kie_service: MagicMock,
    ) -> None:
        """Test generation handles KIE failure."""
        mock_kie_service.wait_for_result = AsyncMock(
            side_effect=KieTaskFailedError("Invalid prompt", fail_code="422")
        )

        ctx = GenerationContext(
            job=test_job,
            user=test_user,
            pricing_variant=test_pricing_variant,
            model=test_model,
            provider=test_provider,
            api_model_id="seedream/4.5-edit",
            media_type="image",
        )

        with pytest.raises(KieTaskFailedError):
            await _execute_generation(
                session=db_session,
                job=test_job,
                ctx=ctx,
                kie_service=mock_kie_service,
                bot=mock_bot,
            )

    @pytest.mark.asyncio
    async def test_execute_generation_timeout(
        self,
        db_session: AsyncSession,
        test_job: GenerationJob,
        test_user: User,
        test_pricing_variant: PricingVariant,
        test_model: AIModel,
        test_provider: Provider,
        mock_bot: MagicMock,
        mock_kie_service: MagicMock,
    ) -> None:
        """Test generation handles timeout."""
        mock_kie_service.wait_for_result = AsyncMock(
            side_effect=KieTaskTimeoutError("kie_task_123", 300.0)
        )

        ctx = GenerationContext(
            job=test_job,
            user=test_user,
            pricing_variant=test_pricing_variant,
            model=test_model,
            provider=test_provider,
            api_model_id="seedream/4.5-edit",
            media_type="image",
        )

        with pytest.raises(KieTaskTimeoutError):
            await _execute_generation(
                session=db_session,
                job=test_job,
                ctx=ctx,
                kie_service=mock_kie_service,
                bot=mock_bot,
            )


class TestProcessGenerationImpl:
    """Tests for _process_generation_impl function."""

    @pytest.mark.asyncio
    async def test_process_generation_job_not_found(
        self, db_session: AsyncSession, mock_bot: MagicMock
    ) -> None:
        """Test handling of non-existent job."""
        # Should not raise, just log error
        await _process_generation_impl(
            job_id=99999,
            session=db_session,
            bot=mock_bot,
        )

    @pytest.mark.asyncio
    async def test_process_generation_wrong_status(
        self,
        db_session: AsyncSession,
        test_job: GenerationJob,
        mock_bot: MagicMock,
    ) -> None:
        """Test skipping job with wrong status."""
        test_job.status = JobStatus.done
        await db_session.commit()

        # Should not raise, just log warning
        await _process_generation_impl(
            job_id=test_job.job_id,
            session=db_session,
            bot=mock_bot,
        )

    @pytest.mark.asyncio
    async def test_process_generation_full_flow_success(
        self,
        db_session: AsyncSession,
        test_job: GenerationJob,
        test_user: User,
        test_pricing_variant: PricingVariant,
        test_model: AIModel,
        test_provider: Provider,
        mock_bot: MagicMock,
    ) -> None:
        """Test full successful generation flow."""
        # Reload job with relationships
        job_repo = GenerationJobRepository(db_session)
        job = await job_repo.get_by_id_for_processing(test_job.job_id)
        assert job is not None

        with patch("app.services.generation.KieClient") as MockKieClient:
            mock_client_instance = MagicMock()
            mock_client_instance.__aenter__ = AsyncMock(
                return_value=mock_client_instance
            )
            mock_client_instance.__aexit__ = AsyncMock(return_value=None)
            MockKieClient.return_value = mock_client_instance

            with patch("app.services.generation.KieService") as MockKieService:
                mock_service = MagicMock()
                mock_service.create_generation = AsyncMock(return_value="kie_task_123")
                mock_service.wait_for_result = AsyncMock(
                    return_value=GenerationResult(
                        task_id="kie_task_123",
                        model="seedream/4.5-edit",
                        result_urls=["https://example.com/result.jpg"],
                        cost_time_ms=5000,
                    )
                )
                MockKieService.return_value = mock_service

                with patch(
                    "services.generation.send_generation_result",
                    new_callable=AsyncMock,
                    return_value="file_id_123",
                ):
                    await _process_generation_impl(
                        job_id=test_job.job_id,
                        session=db_session,
                        bot=mock_bot,
                    )

        # Refresh to get updated values
        await db_session.refresh(test_job)

        assert test_job.status == JobStatus.done
        assert test_job.provider_task_id == "kie_task_123"
        assert test_job.success_url_asset == "https://example.com/result.jpg"

    @pytest.mark.asyncio
    async def test_process_generation_full_flow_error_with_refund(
        self,
        db_session: AsyncSession,
        test_job: GenerationJob,
        test_user: User,
        test_pricing_variant: PricingVariant,
        test_model: AIModel,
        test_provider: Provider,
        mock_bot: MagicMock,
    ) -> None:
        """Test full error flow with refund."""
        # Reload job with relationships
        job_repo = GenerationJobRepository(db_session)
        job = await job_repo.get_by_id_for_processing(test_job.job_id)
        assert job is not None

        with patch("app.services.generation.KieClient") as MockKieClient:
            mock_client_instance = MagicMock()
            mock_client_instance.__aenter__ = AsyncMock(
                return_value=mock_client_instance
            )
            mock_client_instance.__aexit__ = AsyncMock(return_value=None)
            MockKieClient.return_value = mock_client_instance

            with patch("app.services.generation.KieService") as MockKieService:
                mock_service = MagicMock()
                mock_service.create_generation = AsyncMock(return_value="kie_task_123")
                mock_service.wait_for_result = AsyncMock(
                    side_effect=KieTaskFailedError("Content policy violation", "422")
                )
                MockKieService.return_value = mock_service

                with patch(
                    "services.generation.send_generation_error",
                    new_callable=AsyncMock,
                ):
                    await _process_generation_impl(
                        job_id=test_job.job_id,
                        session=db_session,
                        bot=mock_bot,
                    )

        # Refresh to get updated values
        await db_session.refresh(test_job)

        assert test_job.status == JobStatus.error
        assert test_job.error is not None
        assert "Content policy violation" in test_job.error

        # Check refund was created
        tx_repo = TransactionRepository(db_session)
        transactions = await tx_repo.get_user_transactions(test_user.user_id)
        refund = next(
            (t for t in transactions if t.type == TransactionType.refund), None
        )
        assert refund is not None
        assert refund.amount_credits == test_job.cost_credit


class TestProcessKieResult:
    """Tests for terminal callback processing and idempotency."""

    @staticmethod
    def _status(
        state: KieTaskState,
        result_json: str = "",
        fail_message: str = "",
    ) -> TaskStatusData:
        return TaskStatusData(
            taskId="kie_task_callback",
            model="seedream/4.5-edit",
            state=state,
            resultJson=result_json,
            failMsg=fail_message,
            creditsConsumed=3,
        )

    async def test_callback_success_updates_job(
        self,
        db_session: AsyncSession,
        test_job: GenerationJob,
        mock_bot: MagicMock,
    ) -> None:
        test_job.status = JobStatus.processing
        test_job.provider_task_id = "kie_task_callback"
        await db_session.commit()

        status = self._status(
            KieTaskState.success,
            '{"resultUrls":["https://example.com/callback-result.jpg"]}',
        )
        with (
            patch(
                "app.services.generation.send_generation_result",
                new_callable=AsyncMock,
                return_value="telegram-file-id",
            ),
            patch("services.funnel.fire_trigger", new_callable=AsyncMock),
        ):
            await _process_kie_result_impl(
                "kie_task_callback", status, db_session, mock_bot
            )

        await db_session.refresh(test_job)
        assert test_job.status == JobStatus.done
        assert test_job.success_url_asset == ("https://example.com/callback-result.jpg")
        assert test_job.provider_consume_credit == 3

    async def test_callback_failure_refunds_once_on_duplicate(
        self,
        db_session: AsyncSession,
        test_job: GenerationJob,
        test_user: User,
        mock_bot: MagicMock,
    ) -> None:
        test_job.status = JobStatus.processing
        test_job.provider_task_id = "kie_task_callback"
        await db_session.commit()
        status = self._status(KieTaskState.fail, fail_message="Provider failed")

        with patch(
            "app.services.generation.send_generation_error", new_callable=AsyncMock
        ):
            await _process_kie_result_impl(
                "kie_task_callback", status, db_session, mock_bot
            )
            await _process_kie_result_impl(
                "kie_task_callback", status, db_session, mock_bot
            )

        await db_session.refresh(test_job)
        transactions = await TransactionRepository(db_session).get_user_transactions(
            test_user.user_id
        )
        refunds = [tx for tx in transactions if tx.type == TransactionType.refund]
        assert test_job.status == JobStatus.error
        assert test_job.error == "Provider failed"
        assert len(refunds) == 1

    async def test_callback_success_without_result_is_refunded(
        self,
        db_session: AsyncSession,
        test_job: GenerationJob,
        test_user: User,
        mock_bot: MagicMock,
    ) -> None:
        test_job.status = JobStatus.processing
        test_job.provider_task_id = "kie_task_callback"
        await db_session.commit()
        status = self._status(KieTaskState.success, result_json="{}")

        with patch(
            "app.services.generation.send_generation_error", new_callable=AsyncMock
        ):
            await _process_kie_result_impl(
                "kie_task_callback", status, db_session, mock_bot
            )

        await db_session.refresh(test_job)
        transactions = await TransactionRepository(db_session).get_user_transactions(
            test_user.user_id
        )
        assert test_job.status == JobStatus.error
        assert test_job.error == "KIE returned no result URLs"
        assert any(tx.type == TransactionType.refund for tx in transactions)
