"""Funnel messaging service.

Handles data-driven sales funnel:
1. Seed funnel steps from YAML config into DB on startup
2. Fire triggers when user events happen (registration, first generation)
3. Background loop processes due scheduled messages and sends them
"""

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml
from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from core.config import settings
from db.enums import (
    FunnelCondition,
    FunnelTriggerEvent,
    JobStatus,
    ScheduledMessageStatus,
    TransactionType,
)
from db.models.funnel_step import FunnelStep
from db.models.scheduled_message import ScheduledMessage
from db.repositories.funnel_step import FunnelStepRepository
from db.repositories.scheduled_message import ScheduledMessageRepository
from db.session import get_session
from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

_YAML_PATH = Path(__file__).parent.parent.parent / "scripts" / "funnel_steps.yaml"


def _load_yaml() -> list[dict[str, Any]]:
    """Load funnel steps from YAML file."""
    with open(_YAML_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("funnel_steps", [])


async def seed_funnel_steps() -> None:
    """Load steps from funnel_steps.yaml into DB (UPSERT by name).

    Updates all fields except is_active (to preserve manual overrides).
    Inserts new steps as active.
    """
    steps = _load_yaml()
    if not steps:
        logger.warning("funnel_steps.yaml is empty or missing funnel_steps key")
        return

    async with get_session() as session:
        repo = FunnelStepRepository(session)
        for step_data in steps:
            name = step_data["name"]
            existing = await repo.get_by_name(name)
            if existing:
                # Update all fields except is_active
                existing.trigger_event = FunnelTriggerEvent(step_data["trigger_event"])
                existing.delay_seconds = step_data["delay_seconds"]
                existing.condition = (
                    FunnelCondition(step_data["condition"])
                    if step_data.get("condition")
                    else None
                )
                existing.message_text = step_data["message_text"].strip()
                existing.button_text = step_data.get("button_text")
                existing.button_url = step_data.get("button_url")
                await session.flush()
                logger.debug(f"Funnel step updated: {name}")
            else:
                await repo.create(
                    name=name,
                    trigger_event=FunnelTriggerEvent(step_data["trigger_event"]),
                    delay_seconds=step_data["delay_seconds"],
                    condition=(
                        FunnelCondition(step_data["condition"])
                        if step_data.get("condition")
                        else None
                    ),
                    message_text=step_data["message_text"].strip(),
                    button_text=step_data.get("button_text"),
                    button_url=step_data.get("button_url"),
                    is_active=step_data.get("is_active", True),
                )
                logger.debug(f"Funnel step created: {name}")
        await session.commit()

    logger.info(f"Funnel steps seeded: {len(steps)} step(s) from YAML")


async def fire_trigger(
    session: AsyncSession,
    event: FunnelTriggerEvent,
    user_id: int,
    chat_id: int,
) -> None:
    """Find active steps for event and schedule messages for the user.

    Uses ON CONFLICT DO NOTHING via unique constraint (user_id, funnel_step_id).
    """
    step_repo = FunnelStepRepository(session)
    steps = await step_repo.get_active_by_trigger(event)
    if not steps:
        return

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    count = 0
    for step in steps:
        scheduled_at = now + timedelta(seconds=step.delay_seconds)
        # Check if already scheduled (unique constraint will catch duplicates, but
        # we do a soft check first to avoid DB errors in hot paths)
        existing_stmt = select(ScheduledMessage).where(
            ScheduledMessage.user_id == user_id,
            ScheduledMessage.funnel_step_id == step.id,
        )
        result = await session.execute(existing_stmt)
        if result.scalar_one_or_none() is not None:
            continue

        msg = ScheduledMessage(
            user_id=user_id,
            chat_id=chat_id,
            funnel_step_id=step.id,
            scheduled_at=scheduled_at,
            status=ScheduledMessageStatus.pending,
        )
        session.add(msg)
        count += 1

    if count:
        await session.flush()
        logger.info(
            f"Funnel trigger fired: event={event.value}, user_id={user_id}, "
            f"scheduled={count} message(s)"
        )


async def _check_condition(
    session: AsyncSession,
    user_id: int,
    condition: FunnelCondition | None,
) -> bool:
    """Check send condition. True = send, False = skip."""
    if condition is None:
        return True

    if condition == FunnelCondition.no_generation_done:
        from db.models.generation_job import GenerationJob

        stmt = (
            select(func.count())
            .select_from(GenerationJob)
            .where(
                GenerationJob.user_id == user_id,
                GenerationJob.status == JobStatus.done,
            )
        )
        result = await session.execute(stmt)
        count = result.scalar() or 0
        return count == 0

    if condition == FunnelCondition.no_deposit:
        from db.models.transaction import Transaction

        stmt = (
            select(func.count())
            .select_from(Transaction)
            .where(
                Transaction.user_id == user_id,
                Transaction.type == TransactionType.deposit,
            )
        )
        result = await session.execute(stmt)
        count = result.scalar() or 0
        return count == 0

    return True


def _build_keyboard(step: FunnelStep) -> InlineKeyboardMarkup | None:
    """Build inline keyboard for funnel step if button is configured."""
    if not step.button_text or not step.button_url:
        return None
    url = step.button_url.replace("{tma_url}", settings.tma_url)
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=step.button_text, web_app=WebAppInfo(url=url))]
        ]
    )


async def process_due_messages(bot: Bot) -> None:
    """Process all due pending messages: check condition and send or skip."""
    async with get_session() as session:
        msg_repo = ScheduledMessageRepository(session)
        messages = await msg_repo.get_due_pending()

        if not messages:
            return

        logger.info(f"Processing {len(messages)} due funnel message(s)")

        for msg in messages:
            step = msg.funnel_step
            try:
                should_send = await _check_condition(
                    session, msg.user_id, step.condition
                )

                if should_send:
                    keyboard = _build_keyboard(step)
                    await bot.send_message(
                        chat_id=msg.chat_id,
                        text=step.message_text,
                        parse_mode="HTML",
                        reply_markup=keyboard,
                    )
                    msg.status = ScheduledMessageStatus.sent
                    msg.sent_at = datetime.now(timezone.utc).replace(tzinfo=None)
                    logger.info(
                        f"Funnel message sent: id={msg.id}, user_id={msg.user_id}, "
                        f"step={step.name}"
                    )
                else:
                    msg.status = ScheduledMessageStatus.skipped
                    logger.info(
                        f"Funnel message skipped: id={msg.id}, user_id={msg.user_id}, "
                        f"step={step.name}, condition={step.condition}"
                    )
            except Exception:
                logger.exception(
                    f"Failed to process funnel message id={msg.id}, "
                    f"user_id={msg.user_id}"
                )

        await session.commit()


async def funnel_message_loop() -> None:
    """Background loop that periodically sends due funnel messages."""
    from bot import create_bot

    interval = settings.funnel_check_interval_seconds
    logger.info(f"Funnel message loop started (interval={interval}s)")
    try:
        while True:
            await asyncio.sleep(interval)
            bot = create_bot()
            try:
                await process_due_messages(bot)
            except Exception:
                logger.exception("Funnel message loop iteration failed")
            finally:
                await bot.session.close()
    except asyncio.CancelledError:
        logger.info("Funnel message loop stopped")
        raise
