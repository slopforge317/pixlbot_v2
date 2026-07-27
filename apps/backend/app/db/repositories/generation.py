from core.logging import log_repository
from db.enums import JobStatus
from db.models.ai_model import AIModel
from db.models.generation_job import GenerationJob
from db.models.pricing_variant import PricingVariant
from db.repositories.base import BaseRepository
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload


class GenerationJobRepository(BaseRepository[GenerationJob]):
    """Repository for GenerationJob operations."""

    model = GenerationJob

    async def get_user_jobs(
        self, user_id: int, limit: int = 10, offset: int = 0
    ) -> list[GenerationJob]:
        """Get user's generation jobs, newest first."""
        stmt = (
            select(GenerationJob)
            .where(GenerationJob.user_id == user_id)
            .order_by(GenerationJob.created_at.desc())
            .limit(limit)
            .offset(offset)
            .options(selectinload(GenerationJob.pricing_variant))
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_pending_jobs(self, limit: int = 100) -> list[GenerationJob]:
        """Get jobs that need status polling (queue or processing)."""
        stmt = (
            select(GenerationJob)
            .where(GenerationJob.status.in_([JobStatus.queue, JobStatus.processing]))
            .order_by(GenerationJob.created_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_provider_task_id(
        self, provider_task_id: str
    ) -> GenerationJob | None:
        """Get job by provider's task ID."""
        stmt = select(GenerationJob).where(
            GenerationJob.provider_task_id == provider_task_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_jobs_count(
        self, user_id: int, status: JobStatus | None = None
    ) -> int:
        """Count user's jobs, optionally filtered by status."""
        stmt = (
            select(func.count())
            .select_from(GenerationJob)
            .where(GenerationJob.user_id == user_id)
        )
        if status:
            stmt = stmt.where(GenerationJob.status == status)
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    @log_repository
    async def get_user_jobs_filtered(
        self,
        user_id: int,
        status: JobStatus | None = None,
        limit: int = 10,
        offset: int = 0,
    ) -> list[GenerationJob]:
        """Get user's jobs with optional status filter and eager loading."""
        stmt = (
            select(GenerationJob)
            .options(
                selectinload(GenerationJob.pricing_variant)
                .selectinload(PricingVariant.model)
                .selectinload(AIModel.provider)
            )
            .where(GenerationJob.user_id == user_id)
        )
        if status:
            stmt = stmt.where(GenerationJob.status == status)

        stmt = (
            stmt.order_by(GenerationJob.created_at.desc()).limit(limit).offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id_with_mode(self, job_id: int) -> GenerationJob | None:
        """Get job by ID with eager loaded pricing_variant, model, and provider."""
        stmt = (
            select(GenerationJob)
            .options(
                selectinload(GenerationJob.pricing_variant)
                .selectinload(PricingVariant.model)
                .selectinload(AIModel.provider)
            )
            .where(GenerationJob.job_id == job_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    @log_repository
    async def get_by_id_for_processing(self, job_id: int) -> GenerationJob | None:
        """Get job by ID with all relationships needed for processing.

        Loads: user, pricing_variant, model, provider.
        """
        stmt = (
            select(GenerationJob)
            .options(
                selectinload(GenerationJob.user),
                selectinload(GenerationJob.pricing_variant)
                .selectinload(PricingVariant.model)
                .selectinload(AIModel.provider),
            )
            .where(GenerationJob.job_id == job_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    @log_repository
    async def get_by_provider_task_id_for_processing(
        self, provider_task_id: str
    ) -> GenerationJob | None:
        """Get job by provider task ID with all relationships needed for processing.

        Loads: user, pricing_variant, model, provider.
        """
        stmt = (
            select(GenerationJob)
            .options(
                selectinload(GenerationJob.user),
                selectinload(GenerationJob.pricing_variant)
                .selectinload(PricingVariant.model)
                .selectinload(AIModel.provider),
            )
            .where(GenerationJob.provider_task_id == provider_task_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
