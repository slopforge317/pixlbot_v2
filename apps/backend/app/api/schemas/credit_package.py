"""Credit Package API schemas."""

from pydantic import BaseModel, Field, computed_field


class CreditPackageResponse(BaseModel):
    """Credit package response for TMA."""

    id: int
    name: str
    description: str | None
    credit_amount: int
    price: int = Field(validation_alias="fiat_price")  # в копейках

    model_config = {"from_attributes": True}

    @computed_field
    @property
    def price_formatted(self) -> str:
        """Price formatted as '99.00 ₽'."""
        rubles = self.price / 100
        return f"{rubles:.2f} ₽"


class CreditPackageListResponse(BaseModel):
    """List of credit packages response."""

    packages: list[CreditPackageResponse]
