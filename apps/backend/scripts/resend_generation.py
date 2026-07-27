"""
Script for manually resending a generation result to a user via Telegram.

Looks up the generation job by job_id or provider_task_id, finds the result URL
and user chat_id, and sends the file.

Usage:
    PYTHONPATH=app poetry run python scripts/resend_generation.py --job <job_id>
    PYTHONPATH=app poetry run python scripts/resend_generation.py \
        --task <provider_task_id>

Examples:
    PYTHONPATH=app poetry run python scripts/resend_generation.py --job 42
    PYTHONPATH=app poetry run python scripts/resend_generation.py \
        --task 83ab8cbeab6b7fe540664252c0461bfc
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add app to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "app"))

from aiogram import Bot  # noqa: E402
from core.config import settings  # noqa: E402
from db.models.generation_job import GenerationJob  # noqa: E402
from db.session import async_session_maker, engine  # noqa: E402
from services.notification import send_generation_result  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy.orm import joinedload  # noqa: E402


async def resend(job_id: int | None, provider_task_id: str | None) -> None:
    """Find generation job and resend the result."""
    async with async_session_maker() as session:
        stmt = select(GenerationJob).options(
            joinedload(GenerationJob.user),
            joinedload(GenerationJob.pricing_variant),
        )

        if job_id is not None:
            stmt = stmt.where(GenerationJob.job_id == job_id)
        else:
            stmt = stmt.where(GenerationJob.provider_task_id == provider_task_id)

        result = await session.execute(stmt)
        job = result.unique().scalar_one_or_none()

        if not job:
            print("Error: Generation job not found")
            sys.exit(1)

        if not job.success_url_asset:
            print(
                f"Error: Job {job.job_id} has no result URL "
                f"(status: {job.status.value})"
            )
            sys.exit(1)

        user = job.user
        print(f"Job ID:    {job.job_id}")
        print(f"Task ID:   {job.provider_task_id}")
        print(f"Status:    {job.status.value}")
        print(f"User:      {user.first_name} (@{user.username or 'no username'})")
        print(f"Chat ID:   {user.chat_id}")
        print(f"URL:       {job.success_url_asset}")

        # Determine if video from URL extension
        url_lower = job.success_url_asset.lower()
        is_video = any(url_lower.endswith(ext) for ext in (".mp4", ".webm", ".mov"))
        print(f"Type:      {'video' if is_video else 'photo'}")
        print()

        bot = Bot(token=settings.bot_token)
        try:
            file_id = await send_generation_result(
                bot=bot,
                chat_id=user.chat_id,
                result_url=job.success_url_asset,
                is_video=is_video,
            )

            if file_id:
                print(f"Sent successfully! file_id={file_id}")
                if not job.telegram_file_id:
                    job.telegram_file_id = file_id
                    await session.commit()
                    print("Updated telegram_file_id in database")
            else:
                print("Error: Failed to send (see logs for details)")
                sys.exit(1)
        finally:
            await bot.session.close()


async def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Resend a generation result to the user via Telegram"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--job",
        type=int,
        help="Generation job ID (database primary key)",
    )
    group.add_argument(
        "--task",
        type=str,
        help="Provider task ID (e.g. KIE task_id from logs)",
    )

    args = parser.parse_args()
    await resend(job_id=args.job, provider_task_id=args.task)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
