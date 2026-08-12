"""KIE callback authentication and dispatch tests."""

import base64
import hashlib
import hmac
import time
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, patch

import pytest
from api import create_app
from httpx import ASGITransport, AsyncClient

CALLBACK_SECRET = "callback-secret-for-tests"
HMAC_KEY = "webhook-hmac-key-for-tests"


def _payload(task_id: str = "task_123") -> dict[str, object]:
    return {
        "code": 200,
        "msg": "success",
        "data": {
            "taskId": task_id,
            "model": "seedream/5-lite-image-to-image",
            "state": "success",
            "resultJson": '{"resultUrls":["https://example.com/result.png"]}',
            "createTime": 1,
            "updateTime": 2,
        },
    }


def _signature(task_id: str, timestamp: str) -> str:
    digest = hmac.new(
        HMAC_KEY.encode(),
        f"{task_id}.{timestamp}".encode(),
        hashlib.sha256,
    ).digest()
    return base64.b64encode(digest).decode()


@pytest.fixture
async def kie_client() -> AsyncGenerator[tuple[AsyncClient, AsyncMock], None]:
    with (
        patch("api.routes.webhook.settings") as callback_settings,
        patch(
            "api.routes.webhook.process_kie_result", new_callable=AsyncMock
        ) as process_result,
    ):
        callback_settings.kie_callback_secret = CALLBACK_SECRET
        callback_settings.kie_webhook_hmac_key = HMAC_KEY
        callback_settings.kie_webhook_max_age_seconds = 300
        app = create_app()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            yield client, process_result


async def test_kie_callback_accepts_valid_signature(
    kie_client: tuple[AsyncClient, AsyncMock],
) -> None:
    client, process_result = kie_client
    timestamp = str(int(time.time()))

    response = await client.post(
        f"/webhook/kie/{CALLBACK_SECRET}",
        json=_payload(),
        headers={
            "X-Webhook-Timestamp": timestamp,
            "X-Webhook-Signature": _signature("task_123", timestamp),
        },
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    process_result.assert_awaited_once()


async def test_kie_callback_rejects_invalid_signature(
    kie_client: tuple[AsyncClient, AsyncMock],
) -> None:
    client, process_result = kie_client
    timestamp = str(int(time.time()))

    response = await client.post(
        f"/webhook/kie/{CALLBACK_SECRET}",
        json=_payload(),
        headers={
            "X-Webhook-Timestamp": timestamp,
            "X-Webhook-Signature": "invalid",
        },
    )

    assert response.status_code == 403
    process_result.assert_not_awaited()


async def test_kie_callback_rejects_stale_timestamp(
    kie_client: tuple[AsyncClient, AsyncMock],
) -> None:
    client, process_result = kie_client
    timestamp = str(int(time.time()) - 301)

    response = await client.post(
        f"/webhook/kie/{CALLBACK_SECRET}",
        json=_payload(),
        headers={
            "X-Webhook-Timestamp": timestamp,
            "X-Webhook-Signature": _signature("task_123", timestamp),
        },
    )

    assert response.status_code == 403
    process_result.assert_not_awaited()


async def test_kie_callback_rejects_wrong_path_secret(
    kie_client: tuple[AsyncClient, AsyncMock],
) -> None:
    client, process_result = kie_client
    timestamp = str(int(time.time()))

    response = await client.post(
        "/webhook/kie/wrong-secret",
        json=_payload(),
        headers={
            "X-Webhook-Timestamp": timestamp,
            "X-Webhook-Signature": _signature("task_123", timestamp),
        },
    )

    assert response.status_code == 403
    process_result.assert_not_awaited()


async def test_kie_callback_ignores_non_terminal_state(
    kie_client: tuple[AsyncClient, AsyncMock],
) -> None:
    client, process_result = kie_client
    timestamp = str(int(time.time()))
    payload = _payload()
    data = payload["data"]
    assert isinstance(data, dict)
    data["state"] = "generating"

    response = await client.post(
        f"/webhook/kie/{CALLBACK_SECRET}",
        json=payload,
        headers={
            "X-Webhook-Timestamp": timestamp,
            "X-Webhook-Signature": _signature("task_123", timestamp),
        },
    )

    assert response.status_code == 200
    process_result.assert_not_awaited()
