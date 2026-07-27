"""AI Model API schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class PricingVariantResponse(BaseModel):
    """Pricing variant for an AI model."""

    id: int
    variant_values: dict[str, Any]
    price: int

    model_config = {"from_attributes": True}


class AIModelResponse(BaseModel):
    """AI model with pricing variants."""

    id: int
    api_model_id: str
    title: str
    input_schema: dict[str, Any]
    variant_keys: list[str]
    pricing: list[PricingVariantResponse]
    status: str | None = None

    model_config = {"from_attributes": True}


class ProviderResponse(BaseModel):
    """Provider with its models."""

    id: int
    title: str
    gen_type: str
    models: list[AIModelResponse]

    model_config = {"from_attributes": True}


class ProviderListResponse(BaseModel):
    """List of providers."""

    providers: list[ProviderResponse]
