"""Generation API schemas."""

from datetime import UTC, datetime
from typing import Any

from db.enums import JobStatus
from pydantic import BaseModel, Field, field_serializer, field_validator


class ModelInfo(BaseModel):
    """Model info sent by frontend."""

    id: int
    api_model_id: str
    title: str


class VariantInfo(BaseModel):
    """Pricing variant info sent by frontend."""

    id: int
    price: int = Field(..., gt=0)
    variant_values: dict[str, Any] = Field(default_factory=dict)


class GenerationCreateRequest(BaseModel):
    """Request to create a new generation."""

    model: ModelInfo
    variant: VariantInfo
    input: dict[str, Any] = Field(default_factory=dict)

    @field_validator("input")
    @classmethod
    def validate_prompt_in_input(cls, v: dict[str, Any]) -> dict[str, Any]:
        prompt = v.get("prompt")
        if not prompt or not isinstance(prompt, str) or len(prompt.strip()) == 0:
            raise ValueError("prompt is required in input")
        if len(prompt) > 20000:
            raise ValueError("prompt must be at most 20000 characters")
        return v


class GenerationResponse(BaseModel):
    """Generation basic response."""

    job_id: int
    status: JobStatus
    pricing_variant_id: int
    cost_credit: int
    prompt: str
    created_at: datetime

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime) -> str:
        """Serialize DB timestamps as UTC so clients can convert to local time."""
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")

    model_config = {"from_attributes": True}


class GenerationDetailResponse(GenerationResponse):
    """Generation with full details."""

    model_title: str | None = None
    provider_title: str | None = None
    params: dict | None = None
    result_url: str | None = None  # success_url_asset
    error_message: str | None = None
    completed_at: datetime | None = None

    @field_serializer("completed_at")
    def serialize_completed_at(self, value: datetime | None) -> str | None:
        """Serialize provider completion time as UTC when present."""
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


class GenerationListResponse(BaseModel):
    """List of generations with pagination."""

    generations: list[GenerationDetailResponse]
    total: int
    limit: int
    offset: int


class SendOriginalResponse(BaseModel):
    """Response for send-original endpoint."""

    success: bool
    message: str


class InsufficientCreditsError(BaseModel):
    """Insufficient credits error response."""

    detail: str = "Insufficient credits"
    balance: int
    required: int
