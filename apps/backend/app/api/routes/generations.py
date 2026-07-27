"""Generation API endpoints."""

from api.deps import CurrentUser, DBSession
from api.schemas.generation import (
    GenerationCreateRequest,
    GenerationDetailResponse,
    GenerationListResponse,
    GenerationResponse,
    SendOriginalResponse,
)
from db.enums import JobStatus
from db.repositories.generation import GenerationJobRepository
from db.repositories.pricing_variant import PricingVariantRepository
from db.repositories.transaction import TransactionRepository
from db.repositories.user import UserRepository
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from loguru import logger
from services.generation import process_generation

router = APIRouter(prefix="/api", tags=["generations"])


@router.post("/generations", response_model=GenerationResponse, status_code=201)
async def create_generation(
    request: GenerationCreateRequest,
    user: CurrentUser,
    session: DBSession,
    background_tasks: BackgroundTasks,
) -> GenerationResponse:
    """
    Create a new generation job.

    Checks balance, deducts credits, and queues the job.
    """
    logger.info(
        f"Creating generation: user_id={user.user_id}, "
        f"variant_id={request.variant.id}, "
        f"prompt_length={len(request.input['prompt'])}"
    )

    # 1. Validate pricing variant exists and is active
    pv_repo = PricingVariantRepository(session)
    variant = await pv_repo.get_by_id(request.variant.id)

    if not variant or not variant.active:
        logger.warning(
            f"Pricing variant not found or inactive: "
            f"variant_id={request.variant.id}"
        )
        raise HTTPException(
            status_code=404, detail="Pricing variant not found or inactive"
        )

    # 2. Price check (stale data protection)
    if request.variant.price != variant.price:
        logger.warning(
            f"Price mismatch: client sent {request.variant.price}, "
            f"DB has {variant.price}, variant_id={variant.id}"
        )
        raise HTTPException(
            status_code=409,
            detail="Price has changed. Please refresh and try again.",
        )

    # 3. Check user balance
    user_repo = UserRepository(session)
    balance = await user_repo.get_balance(user.user_id)

    if balance < variant.price:
        logger.warning(
            f"Insufficient credits: user_id={user.user_id}, "
            f"balance={balance}, required={variant.price}"
        )
        raise HTTPException(
            status_code=400,
            detail={
                "detail": "Insufficient credits",
                "balance": balance,
                "required": variant.price,
            },
        )

    # 4. Extract prompt, create generation job
    prompt = request.input["prompt"].strip()

    job_repo = GenerationJobRepository(session)
    job = await job_repo.create(
        user_id=user.user_id,
        pricing_variant_id=variant.id,
        status=JobStatus.queue,
        cost_credit=variant.price,
        prompt=prompt,
        generation_params=request.input,
    )

    # 5. Deduct credits
    tx_repo = TransactionRepository(session)
    await tx_repo.create_withdrawal(
        user_id=user.user_id,
        amount_credits=variant.price,
        job_id=job.job_id,
    )

    # Calculate balance after deduction
    balance_after = balance - variant.price
    logger.info(
        f"Job created: job_id={job.job_id}, cost={variant.price}, "
        f"balance_after={balance_after}"
    )

    # 6. Commit transaction before background task
    # IMPORTANT: Must commit here so background task (which uses its own session)
    # can see the job. Without this, there's a race condition where the background
    # task starts before the dependency cleanup commits the transaction.
    await session.commit()

    # 7. Queue background task for KIE API
    background_tasks.add_task(process_generation, job.job_id)

    return GenerationResponse(
        job_id=job.job_id,
        status=job.status,
        pricing_variant_id=job.pricing_variant_id,
        cost_credit=job.cost_credit,
        prompt=job.prompt,
        created_at=job.created_at,
    )


@router.get("/generations", response_model=GenerationListResponse)
async def list_generations(
    user: CurrentUser,
    session: DBSession,
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0),
    status: JobStatus | None = Query(None),
) -> GenerationListResponse:
    """Get user's generation history with pagination."""
    logger.debug(
        f"Listing generations: user_id={user.user_id}, "
        f"limit={limit}, offset={offset}, status={status}"
    )
    job_repo = GenerationJobRepository(session)

    # Get jobs (filtered by status if provided)
    jobs = await job_repo.get_user_jobs_filtered(
        user.user_id, status=status, limit=limit, offset=offset
    )

    # Get total count for pagination
    total = await job_repo.get_user_jobs_count(user.user_id, status=status)

    generations = []
    for job in jobs:
        pv = job.pricing_variant
        model = pv.model if pv else None
        provider = model.provider if model else None

        gen = GenerationDetailResponse(
            job_id=job.job_id,
            status=job.status,
            pricing_variant_id=job.pricing_variant_id,
            cost_credit=job.cost_credit,
            prompt=job.prompt,
            created_at=job.created_at,
            model_title=model.title if model else None,
            provider_title=provider.title if provider else None,
            result_url=job.success_url_asset,
            params=job.generation_params,
        )
        generations.append(gen)

    return GenerationListResponse(
        generations=generations,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/generations/{job_id}", response_model=GenerationDetailResponse)
async def get_generation(
    job_id: int,
    user: CurrentUser,
    session: DBSession,
) -> GenerationDetailResponse:
    """Get details of a specific generation job."""
    logger.debug(f"Getting generation: job_id={job_id}, user_id={user.user_id}")
    job_repo = GenerationJobRepository(session)
    job = await job_repo.get_by_id_with_mode(job_id)

    if not job or job.user_id != user.user_id:
        logger.warning(
            f"Generation not found or access denied: job_id={job_id}, "
            f"user_id={user.user_id}"
        )
        raise HTTPException(status_code=404, detail="Generation not found")

    pv = job.pricing_variant
    model = pv.model if pv else None
    provider = model.provider if model else None

    return GenerationDetailResponse(
        job_id=job.job_id,
        status=job.status,
        pricing_variant_id=job.pricing_variant_id,
        cost_credit=job.cost_credit,
        prompt=job.prompt,
        created_at=job.created_at,
        model_title=model.title if model else None,
        provider_title=provider.title if provider else None,
        params=job.generation_params,
        result_url=job.success_url_asset,
        error_message=job.error,
        completed_at=job.provider_complete_time,
    )


@router.post(
    "/generations/{job_id}/send-original",
    response_model=SendOriginalResponse,
)
async def send_original(
    job_id: int,
    user: CurrentUser,
    session: DBSession,
) -> SendOriginalResponse:
    """Send generation result as document (original quality) to user's Telegram chat."""
    from bot import create_bot
    from services.notification import send_original_document

    logger.debug(f"Send original: job_id={job_id}, user_id={user.user_id}")

    job_repo = GenerationJobRepository(session)
    job = await job_repo.get_by_id_with_mode(job_id)

    if not job or job.user_id != user.user_id:
        raise HTTPException(status_code=404, detail="Generation not found")

    if job.status != JobStatus.done:
        raise HTTPException(status_code=400, detail="Generation is not completed")

    if not job.success_url_asset:
        raise HTTPException(status_code=400, detail="No result file available")

    pv = job.pricing_variant
    model = pv.model if pv else None
    provider = model.provider if model else None
    provider_title = (provider.title if provider else "").lower()
    is_video = any(v in provider_title for v in ("veo", "kling", "sora"))

    bot = create_bot()
    try:
        await send_original_document(
            bot=bot,
            chat_id=user.chat_id,
            result_url=job.success_url_asset,
            is_video=is_video,
        )
    except Exception as e:
        logger.error(f"Failed to send original: job_id={job_id}, error={e}")
        raise HTTPException(
            status_code=502,
            detail="Failed to send document to Telegram",
        )
    finally:
        await bot.session.close()

    return SendOriginalResponse(success=True, message="Document sent")
