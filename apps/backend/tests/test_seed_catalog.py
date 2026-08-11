"""Tests for model catalog seed validation."""

from copy import deepcopy

import pytest

from scripts.seed_db import (
    load_api_parameters,
    load_seed_prices,
    normalize_input_schema,
    validate_catalog,
)


def test_current_catalog_is_valid_and_contains_only_images() -> None:
    api_params = load_api_parameters()
    prices = load_seed_prices()

    validate_catalog(api_params, prices)

    assert {entry["gen_type"] for entry in api_params} == {"image"}


def test_gpt_image_quality_is_pricing_variant_for_both_modes() -> None:
    gpt_entries = [
        entry for entry in load_api_parameters() if entry["slug"] == "gpt-image-1-5"
    ]

    assert {entry["model"]["input_mode"] for entry in gpt_entries} == {
        "text_only",
        "image_required",
    }
    assert all(
        entry["input"]["parameters"]["quality"]["variant"] is True
        for entry in gpt_entries
    )


def test_gpt_image_2_uses_only_resolution_pricing_and_supports_16_images() -> None:
    entries = [
        entry for entry in load_api_parameters() if entry["slug"] == "gpt-image-2"
    ]
    prices = load_seed_prices()

    assert {entry["model"]["values"][0] for entry in entries} == {
        "gpt-image-2-text-to-image",
        "gpt-image-2-image-to-image",
    }
    assert all(
        entry["input"]["parameters"]["resolution"]["values"] == ["2K", "4K"]
        for entry in entries
    )
    assert all(
        entry["input"]["parameters"]["resolution"]["variant"] is True
        for entry in entries
    )
    for model_id in (
        "gpt-image-2-text-to-image",
        "gpt-image-2-image-to-image",
    ):
        assert {
            (price["variant_values"]["resolution"], price["price"])
            for price in prices[model_id]
        } == {("2K", 3), ("4K", 4)}

    image_entry = next(
        entry for entry in entries if entry["model"]["input_mode"] == "image_required"
    )
    assert image_entry["input"]["parameters"]["input_urls"]["max_images"] == 16
    assert image_entry["input"]["parameters"]["prompt"]["max_length"] == 20000


def test_catalog_rejects_pricing_keys_not_marked_as_variants() -> None:
    api_params = deepcopy(load_api_parameters())
    prices = load_seed_prices()
    gpt_image_to_image = next(
        entry
        for entry in api_params
        if entry["model"]["values"] == ["gpt-image/1.5-image-to-image"]
    )
    gpt_image_to_image["input"]["parameters"]["quality"]["variant"] = False

    with pytest.raises(ValueError, match="Pricing keys"):
        validate_catalog(api_params, prices)


def test_input_schema_has_stable_field_and_option_order() -> None:
    schema = normalize_input_schema(
        {
            "quality": {
                "type": "string",
                "ui_order": 2,
                "values": ["medium", "high"],
            }
        }
    )

    assert schema["quality"]["ui_order"] == 20
    assert schema["quality"]["options"] == [
        {"value": "medium", "label": "medium", "sort_order": 10},
        {"value": "high", "label": "high", "sort_order": 20},
    ]
    assert "values" not in schema["quality"]
