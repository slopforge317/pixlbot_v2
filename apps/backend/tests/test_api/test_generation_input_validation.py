"""Model-specific generation input validation tests."""

import pytest
from api.routes.generations import _validate_input_against_model
from db.models.ai_model import AIModel
from fastapi import HTTPException


def make_model(input_schema: dict) -> AIModel:
    return AIModel(
        provider_id=1,
        api_model_id="test/image-to-image",
        title="Image-to-Image",
        input_mode="image_required",
        input_schema=input_schema,
        variant_keys=[],
    )


def test_accepts_model_prompt_and_image_limits() -> None:
    model = make_model(
        {
            "prompt": {"type": "string", "max_length": 5},
            "image_urls": {"type": "array", "required": True, "max_images": 2},
        }
    )

    _validate_input_against_model(
        {"prompt": "12345", "image_urls": ["one", "two"]}, model, user_id=1
    )


def test_rejects_prompt_over_model_limit() -> None:
    model = make_model({"prompt": {"type": "string", "max_length": 5}})

    with pytest.raises(HTTPException, match="Prompt must be at most 5"):
        _validate_input_against_model({"prompt": "123456"}, model, user_id=1)


def test_rejects_too_many_reference_images() -> None:
    model = make_model(
        {
            "prompt": {"type": "string", "max_length": 20},
            "image_urls": {"type": "array", "required": True, "max_images": 1},
        }
    )

    with pytest.raises(HTTPException, match="accepts at most 1 images"):
        _validate_input_against_model(
            {"prompt": "ok", "image_urls": ["one", "two"]}, model, user_id=1
        )


def test_rejects_missing_required_reference_image() -> None:
    model = make_model(
        {
            "prompt": {"type": "string", "max_length": 20},
            "image_urls": {"type": "array", "required": True, "max_images": 1},
        }
    )

    with pytest.raises(HTTPException, match="requires at least one image"):
        _validate_input_against_model({"prompt": "ok"}, model, user_id=1)


def test_rejects_reference_owned_by_another_user() -> None:
    model = make_model(
        {
            "prompt": {"type": "string"},
            "image_urls": {"type": "array", "required": True, "max_images": 1},
        }
    )
    foreign_key = "uploads/2/550e8400-e29b-41d4-a716-446655440000.jpg"

    with pytest.raises(HTTPException, match="owned by another user"):
        _validate_input_against_model(
            {"prompt": "ok", "image_urls": [foreign_key]}, model, user_id=1
        )
