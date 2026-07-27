"""Generation processing service.

Handles the full generation lifecycle:
1. Send task to KIE API
2. Poll for completion (or await callback in production)
3. Update job status in DB
4. Send result/error notification to user via bot
5. Refund credits on error
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from bot import create_bot
from bot.texts import GENERATION_SUCCESS
from core.config import settings
from core.logging import set_job_id
from db.enums import JobStatus
from db.models.ai_model import AIModel
from db.models.generation_job import GenerationJob
from db.models.pricing_variant import PricingVariant
from db.models.provider import Provider
from db.models.user import User
from db.repositories.generation import GenerationJobRepository
from db.repositories.transaction import TransactionRepository
from db.session import get_session
from loguru import logger
from services.kie import (
    GenerationResult,
    KieAPIError,
    KieClient,
    KieService,
    KieTaskFailedError,
    KieTaskTimeoutError,
)
from services.kie.schemas import TaskStatusData
from services.notification import (
    send_generation_error,
    send_generation_result,
    send_generation_timeout,
)
from services.storage.service import is_valid_object_key
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class GenerationContext:
    """Context for generation processing."""

    job: GenerationJob
    user: User
    pricing_variant: PricingVariant
    model: AIModel
    provider: Provider
    api_model_id: str
    media_type: str  # "image" or "video"


async def process_generation(job_id: int) -> None:
    """Entry point for background task.

    Creates its own DB session and bot instance since FastAPI session
    will be closed after the response is sent.

    Args:
        job_id: ID of the GenerationJob to process
    """
    # Set job context for logging
    set_job_id(job_id)
    logger.info("Generation processing started")

    async with get_session() as session:
        bot = create_bot()
        try:
            await _process_generation_impl(job_id, session, bot)
        finally:
            await bot.session.close()
            set_job_id(None)


async def _process_generation_impl(
    job_id: int,
    session: AsyncSession,
    bot: Any,
) -> None:
    """Implementation of generation processing.

    Args:
        job_id: ID of the GenerationJob to process
        session: Database session
        bot: Telegram bot instance
    """
    job_repo = GenerationJobRepository(session)
    tx_repo = TransactionRepository(session)

    # 1. Load job with related data (user, pricing_variant, model, provider)
    job = await job_repo.get_by_id_for_processing(job_id)
    if not job:
        logger.error("Job not found")
        return

    if job.status not in (JobStatus.queue, JobStatus.processing):
        logger.warning(f"Job has unexpected status: {job.status}")
        return

    # Get user for chat_id
    user = job.user
    if not user:
        logger.error("Job has no associated user")
        return

    variant = job.pricing_variant
    if not variant:
        logger.error("Job has no associated pricing variant")
        await _handle_error(
            session,
            job,
            user,
            bot,
            tx_repo,
            "Configuration error: pricing variant not found",
        )
        return

    model = variant.model
    if not model:
        logger.error("Pricing variant has no associated model")
        await _handle_error(
            session, job, user, bot, tx_repo, "Configuration error: model not found"
        )
        return

    provider = model.provider
    if not provider:
        logger.error("Model has no associated provider")
        await _handle_error(
            session, job, user, bot, tx_repo, "Configuration error: provider not found"
        )
        return

    logger.debug(
        f"Job loaded: user_id={user.user_id}, model={model.api_model_id}, "
        f"cost={job.cost_credit}"
    )

    # 2. Build context
    ctx = _build_context(job, user, variant, model, provider)

    # 3. Update status to processing
    old_status = job.status
    job.status = JobStatus.processing
    await session.commit()
    logger.info(f"Job status changed: {old_status.value} -> {job.status.value}")

    # 4. Create KIE service and process generation
    async with KieClient(
        api_key=settings.kie_api_key,
        base_url=settings.kie_api_base_url,
    ) as client:
        kie_service = KieService(
            client=client,
            poll_interval=settings.kie_poll_interval,
            timeout=settings.kie_poll_timeout,
        )

        try:
            await _execute_generation(session, job, ctx, kie_service, bot)
        except KieTaskTimeoutError as e:
            logger.warning(f"Job timed out: {e}")
            await _handle_timeout(session, job, user, bot, tx_repo)
        except KieTaskFailedError as e:
            logger.warning(f"Job failed in KIE: {e.message}")
            await _handle_error(session, job, user, bot, tx_repo, e.message)
        except KieAPIError as e:
            logger.error(f"KIE API error: {e.message}")
            await _handle_error(
                session, job, user, bot, tx_repo, f"API error: {e.message}"
            )
        except Exception as e:
            logger.exception(f"Unexpected error: {e}")
            await _handle_error(
                session, job, user, bot, tx_repo, "Unexpected error occurred"
            )


def _build_context(
    job: GenerationJob,
    user: User,
    variant: PricingVariant,
    model: AIModel,
    provider: Provider,
) -> GenerationContext:
    """Build generation context from job and related entities.

    Args:
        job: Generation job
        user: User who created the job
        variant: Pricing variant
        model: AI model
        provider: Provider

    Returns:
        GenerationContext with extracted parameters
    """
    return GenerationContext(
        job=job,
        user=user,
        pricing_variant=variant,
        model=model,
        provider=provider,
        api_model_id=model.api_model_id,
        media_type=provider.gen_type,
    )


def _replace_object_keys_with_urls(input_data: dict[str, Any]) -> dict[str, Any]:
    """Replace S3 object keys with presigned GET URLs in input data.

    Scans input_data values; if a value is a list[str] where all items
    match OBJECT_KEY_PATTERN, replaces each with a presigned GET URL.
    Base64 data URIs don't match the pattern and pass through unchanged.

    Args:
        input_data: Generation input data dict

    Returns:
        Modified input_data with object keys replaced by presigned GET URLs
    """
    from services.storage import get_storage_service

    storage = get_storage_service()

    for key, value in input_data.items():
        if not isinstance(value, list):
            continue
        if not value:
            continue
        if not all(isinstance(item, str) for item in value):
            continue
        if not all(is_valid_object_key(item) for item in value):
            continue

        # All items are valid object keys — replace with presigned GET URLs
        input_data[key] = [
            storage.generate_presigned_get_url(obj_key) for obj_key in value
        ]
        logger.debug(
            f"Replaced {len(value)} object key(s) with presigned GET URLs "
            f"for field '{key}'"
        )

    return input_data


async def _execute_generation(
    session: AsyncSession,
    job: GenerationJob,
    ctx: GenerationContext,
    kie_service: KieService,
    bot: Any,
) -> None:
    """Execute the generation via KIE API.

    Args:
        session: Database session
        job: Generation job
        ctx: Generation context
        kie_service: KIE service instance
        bot: Telegram bot instance
    """
    # Build input for KIE from generation_params
    input_data: dict[str, Any] = {}
    if job.generation_params:
        input_data = dict(job.generation_params)

    # Ensure prompt from DB column (authoritative)
    input_data["prompt"] = job.prompt

    # Replace S3 object keys with presigned GET URLs
    try:
        input_data = _replace_object_keys_with_urls(input_data)
    except Exception as e:
        logger.warning(f"Failed to replace object keys with URLs: {e}")

    # 5. Build callback URL if callback mode is enabled
    callback_url = None
    if settings.kie_callback_enabled and settings.webhook_base_url:
        callback_url = (
            f"{settings.webhook_base_url}/webhook/kie/"
            f"{settings.kie_callback_secret}"
        )

    # 6. Create task in KIE API
    task_id = await kie_service.create_generation(
        model=ctx.api_model_id,
        input_data=input_data,
        callback_url=callback_url,
    )

    # 7. Save provider_task_id
    job.provider_task_id = task_id
    await session.commit()
    logger.info(f"KIE task created: kie_task_id={task_id}, model={ctx.api_model_id}")

    # 8. In callback mode, return immediately — result comes via webhook
    if settings.kie_callback_enabled:
        logger.info(f"Callback mode: task_id={task_id}, awaiting webhook")
        return

    # 9. Wait for result (polling)
    result = await kie_service.wait_for_result(task_id)

    # 10. Handle success
    await _handle_success(session, job, ctx.user, bot, result, ctx.media_type)


async def _handle_success(
    session: AsyncSession,
    job: GenerationJob,
    user: User,
    bot: Any,
    result: GenerationResult,
    media_type: str,
) -> None:
    """Handle successful generation: update job, send result to user.

    Args:
        session: Database session
        job: Generation job
        user: User who created the job
        bot: Telegram bot instance
        result: Generation result from KIE
        media_type: "image" or "video"
    """
    job.status = JobStatus.done
    job.provider_complete_time = datetime.utcnow()

    if result.result_urls:
        job.success_url_asset = result.result_urls[0]

    await session.commit()
    logger.info("Generation completed successfully")

    # Fire funnel trigger on first successful generation
    try:
        done_count = await GenerationJobRepository(session).get_user_jobs_count(
            user.user_id, status=JobStatus.done
        )
        if done_count == 1:
            from db.enums import FunnelTriggerEvent
            from services.funnel import fire_trigger

            await fire_trigger(
                session,
                FunnelTriggerEvent.first_generation_done,
                user.user_id,
                user.chat_id,
            )
            await session.commit()
    except Exception:
        logger.exception("Failed to fire first_generation_done funnel trigger")

    if job.success_url_asset:
        is_video = media_type == "video"
        file_id = await send_generation_result(
            bot=bot,
            chat_id=user.chat_id,
            result_url=job.success_url_asset,
            is_video=is_video,
            caption=GENERATION_SUCCESS,
        )

        if file_id:
            job.telegram_file_id = file_id
            await session.commit()


async def _handle_error(
    session: AsyncSession,
    job: GenerationJob,
    user: User,
    bot: Any,
    tx_repo: TransactionRepository,
    error_message: str,
) -> None:
    """Handle generation error: update status, refund, notify.

    Args:
        session: Database session
        job: Generation job
        user: User who created the job
        bot: Telegram bot instance
        tx_repo: Transaction repository
        error_message: Human-readable error description
    """
    # Update job status
    job.status = JobStatus.error
    job.error = error_message
    await session.commit()

    # Refund credits
    await tx_repo.create_refund(
        user_id=user.user_id,
        amount_credits=job.cost_credit,
        job_id=job.job_id,
    )
    await session.commit()
    logger.info(
        f"Credits refunded: user_id={user.user_id}, "
        f"amount={job.cost_credit}, reason=error"
    )

    # Send notification
    await send_generation_error(
        bot=bot,
        chat_id=user.chat_id,
        error_message=error_message,
        credits_refunded=job.cost_credit,
    )


async def _handle_timeout(
    session: AsyncSession,
    job: GenerationJob,
    user: User,
    bot: Any,
    tx_repo: TransactionRepository,
) -> None:
    """Handle generation timeout: update status, refund, notify.

    Args:
        session: Database session
        job: Generation job
        user: User who created the job
        bot: Telegram bot instance
        tx_repo: Transaction repository
    """
    # Update job status
    job.status = JobStatus.error
    job.error = "Generation timed out"
    await session.commit()

    # Refund credits
    await tx_repo.create_refund(
        user_id=user.user_id,
        amount_credits=job.cost_credit,
        job_id=job.job_id,
    )
    await session.commit()
    logger.info(
        f"Credits refunded: user_id={user.user_id}, "
        f"amount={job.cost_credit}, reason=timeout"
    )

    # Send notification
    await send_generation_timeout(
        bot=bot,
        chat_id=user.chat_id,
        credits_refunded=job.cost_credit,
    )


async def process_kie_result(task_id: str, task_status: TaskStatusData) -> None:
    """Process KIE callback result. Called by webhook handler.

    Creates its own DB session and bot instance.

    Args:
        task_id: KIE task ID
        task_status: Task status data from KIE callback
    """
    set_job_id(None)
    logger.info(
        f"Processing KIE callback: task_id={task_id}, state={task_status.state}"
    )

    async with get_session() as session:
        bot = create_bot()
        try:
            job_repo = GenerationJobRepository(session)
            tx_repo = TransactionRepository(session)

            job = await job_repo.get_by_provider_task_id_for_processing(task_id)
            if not job:
                logger.error(f"Job not found for provider_task_id={task_id}")
                return

            set_job_id(job.job_id)

            # Idempotency: skip if already in terminal state
            if job.status in (JobStatus.done, JobStatus.error):
                logger.warning(
                    f"Job already in terminal state: {job.status.value}, skipping"
                )
                return

            user = job.user
            if not user:
                logger.error("Job has no associated user")
                return

            variant = job.pricing_variant
            if not variant or not variant.model or not variant.model.provider:
                logger.error("Job missing required relationships")
                await _handle_error(
                    session,
                    job,
                    user,
                    bot,
                    tx_repo,
                    "Configuration error: missing relationships",
                )
                return

            media_type = variant.model.provider.gen_type

            if task_status.state.is_success():
                result = GenerationResult.from_task_status(task_status)
                await _handle_success(session, job, user, bot, result, media_type)
            else:
                error_msg = task_status.failMsg or "Generation failed"
                await _handle_error(session, job, user, bot, tx_repo, error_msg)
        except Exception as e:
            logger.exception(f"Error processing KIE callback: {e}")
        finally:
            await bot.session.close()
            set_job_id(None)
