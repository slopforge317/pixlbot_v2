"""Webhook endpoints for Telegram, KIE callbacks, and YooKassa."""

import asyncio
import base64
import hashlib
import hmac
import ipaddress
import time
from typing import Any

from aiogram.types import Update
from core.config import settings
from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request
from loguru import logger
from pydantic import ValidationError
from services.generation import process_kie_result
from services.kie.schemas import TaskStatusResponse
from services.payment import process_yookassa_notification

# YooKassa trusted IP ranges
# https://yookassa.ru/developers/using-api/webhooks
YOOKASSA_IP_NETWORKS = [
    ipaddress.ip_network("185.71.76.0/27"),
    ipaddress.ip_network("185.71.77.0/27"),
    ipaddress.ip_network("77.75.153.0/25"),
    ipaddress.ip_network("77.75.156.11/32"),
    ipaddress.ip_network("77.75.156.35/32"),
    ipaddress.ip_network("77.75.154.128/25"),
    ipaddress.ip_network("2a02:5180::/32"),
]

router = APIRouter(tags=["webhook"])


@router.post("/webhook/telegram")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(None),
) -> dict[str, bool]:
    """
    Handle incoming Telegram updates via webhook.

    Telegram sends updates to this endpoint when webhook is configured.
    The secret token header is verified to ensure requests come from Telegram.
    """
    logger.debug("Webhook request received")

    # Get client IP for logging
    client_ip = request.headers.get("X-Forwarded-For")
    if client_ip:
        client_ip = client_ip.split(",")[0].strip()
    else:
        client_ip = request.client.host if request.client else "unknown"

    # Verify secret token
    if x_telegram_bot_api_secret_token != settings.webhook_secret:
        logger.warning(f"Invalid webhook secret token from {client_ip}")
        raise HTTPException(status_code=403, detail="Invalid secret token")

    # Get bot and dispatcher from app state
    bot = getattr(request.app.state, "bot", None)
    dispatcher = getattr(request.app.state, "dispatcher", None)

    if bot is None or dispatcher is None:
        logger.error("Bot or dispatcher not initialized in app state")
        raise HTTPException(status_code=500, detail="Bot not initialized")

    # Parse and process update
    try:
        data = await request.json()
        update = Update.model_validate(data, context={"bot": bot})

        # Determine update type for logging
        update_type = "unknown"
        if update.message:
            update_type = "message"
        elif update.callback_query:
            update_type = "callback_query"
        elif update.inline_query:
            update_type = "inline_query"

        logger.info(
            f"Processing Telegram update: "
            f"update_id={update.update_id}, type={update_type}"
        )

        await dispatcher.feed_update(bot, update)
    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
        # Return 200 anyway to prevent Telegram from retrying
        # Errors are logged for debugging

    return {"ok": True}


def _verify_kie_signature(
    task_id: str,
    timestamp: str | None,
    signature: str | None,
) -> None:
    """Verify KIE HMAC signature and reject stale callback requests."""
    if not settings.kie_webhook_hmac_key:
        logger.error("KIE webhook HMAC key is not configured")
        raise HTTPException(status_code=503, detail="Callback is not configured")

    if not timestamp or not signature:
        raise HTTPException(status_code=403, detail="Missing webhook signature")

    try:
        timestamp_seconds = int(timestamp)
    except ValueError as exc:
        raise HTTPException(
            status_code=403, detail="Invalid webhook timestamp"
        ) from exc

    if abs(int(time.time()) - timestamp_seconds) > settings.kie_webhook_max_age_seconds:
        raise HTTPException(status_code=403, detail="Stale webhook timestamp")

    message = f"{task_id}.{timestamp}".encode()
    digest = hmac.new(
        settings.kie_webhook_hmac_key.encode(),
        message,
        hashlib.sha256,
    ).digest()
    expected_signature = base64.b64encode(digest).decode()
    if not hmac.compare_digest(expected_signature, signature):
        raise HTTPException(status_code=403, detail="Invalid webhook signature")


@router.post("/webhook/kie/{secret}")
async def kie_callback(
    secret: str,
    request: Request,
    background_tasks: BackgroundTasks,
    x_webhook_timestamp: str | None = Header(None),
    x_webhook_signature: str | None = Header(None),
) -> dict[str, bool]:
    """Handle KIE generation callback.

    KIE sends task results to this endpoint when callback mode is enabled.
    The secret path parameter prevents unauthorized access.
    """
    if not settings.kie_callback_secret or not hmac.compare_digest(
        secret, settings.kie_callback_secret
    ):
        logger.warning("Invalid KIE callback secret")
        raise HTTPException(status_code=403, detail="Invalid secret")

    try:
        body: Any = await request.json()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON") from exc

    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="Invalid callback payload")

    data = body.get("data")
    task_id = data.get("taskId") if isinstance(data, dict) else None
    if not isinstance(task_id, str) or not task_id:
        raise HTTPException(status_code=400, detail="Missing taskId")

    _verify_kie_signature(task_id, x_webhook_timestamp, x_webhook_signature)
    logger.debug(f"KIE callback received: task_id={task_id}")

    try:
        response = TaskStatusResponse.model_validate(body)
    except ValidationError as exc:
        logger.warning(f"Invalid KIE callback payload: task_id={task_id}")
        raise HTTPException(status_code=400, detail="Invalid callback payload") from exc

    if not response.data:
        logger.warning("KIE callback has no data")
        return {"ok": True}

    if not response.data.state.is_terminal():
        logger.info(
            f"Ignoring non-terminal KIE callback: "
            f"task_id={task_id}, state={response.data.state.value}"
        )
        return {"ok": True}

    background_tasks.add_task(process_kie_result, task_id, response.data)

    return {"ok": True}


def _is_yookassa_ip(ip_str: str) -> bool:
    """Check if IP address belongs to YooKassa trusted ranges."""
    try:
        addr = ipaddress.ip_address(ip_str)
        return any(addr in network for network in YOOKASSA_IP_NETWORKS)
    except ValueError:
        return False


@router.post("/webhook/yookassa")
async def yookassa_webhook(request: Request) -> dict[str, bool]:
    """Handle YooKassa payment notifications.

    Verifies the request comes from YooKassa IP ranges,
    then processes the payment notification asynchronously.
    """
    # Prefer the client IP supplied by the trusted reverse proxy.
    client_ip = request.headers.get("X-Real-IP")
    if not client_ip:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"

    # Verify IP
    if not _is_yookassa_ip(client_ip):
        logger.warning(f"YooKassa webhook rejected: untrusted IP {client_ip}")
        raise HTTPException(status_code=403, detail="Forbidden")

    body = await request.json()
    logger.debug(f"YooKassa webhook payload: {body}")

    event = body.get("event")
    payment_object = body.get("object", {})
    yookassa_payment_id = payment_object.get("id")

    if not event or not yookassa_payment_id:
        logger.warning("YooKassa webhook: missing event or object.id")
        return {"ok": True}

    asyncio.create_task(
        process_yookassa_notification(event, yookassa_payment_id, payment_object)
    )

    return {"ok": True}
