"""KIE callback configuration tests without external services."""

import pytest
from services import generation


def _configured_settings() -> dict[str, object]:
    return {
        "kie_api_key": "api-key",
        "webhook_base_url": "https://tma.pixlbot.ru/",
        "kie_callback_secret": "callback-secret",
        "kie_webhook_hmac_key": "hmac-key",
        "kie_webhook_max_age_seconds": 300,
        "kie_reconciliation_interval_seconds": 60,
        "kie_reconciliation_stale_seconds": 60,
        "kie_reconciliation_batch_size": 100,
    }


def _apply_settings(
    monkeypatch: pytest.MonkeyPatch, configured: dict[str, object]
) -> None:
    for name, value in configured.items():
        monkeypatch.setattr(generation.settings, name, value)


def test_builds_callback_url_from_origin(monkeypatch: pytest.MonkeyPatch) -> None:
    _apply_settings(monkeypatch, _configured_settings())

    assert generation.build_kie_callback_url() == (
        "https://tma.pixlbot.ru/webhook/kie/callback-secret"
    )


def test_requires_hmac_key(monkeypatch: pytest.MonkeyPatch) -> None:
    configured = _configured_settings()
    configured["kie_webhook_hmac_key"] = ""
    _apply_settings(monkeypatch, configured)

    with pytest.raises(RuntimeError, match="KIE_WEBHOOK_HMAC_KEY"):
        generation.build_kie_callback_url()


def test_rejects_base_url_with_path(monkeypatch: pytest.MonkeyPatch) -> None:
    configured = _configured_settings()
    configured["webhook_base_url"] = "https://tma.pixlbot.ru/api"
    _apply_settings(monkeypatch, configured)

    with pytest.raises(RuntimeError, match="without a path"):
        generation.build_kie_callback_url()
