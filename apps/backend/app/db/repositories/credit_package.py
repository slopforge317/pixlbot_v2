from db.models.credit_package import CreditPackage
from db.repositories.base import BaseRepository
from sqlalchemy import select


class CreditPackageRepository(BaseRepository[CreditPackage]):
    """Repository for CreditPackage operations."""

    model = CreditPackage

    async def get_active(
        self, limit: int = 100, offset: int = 0
    ) -> list[CreditPackage]:
        """Get all active credit packages with pagination."""
        stmt = (
            select(CreditPackage)
            .where(CreditPackage.is_active == True)  # noqa: E712
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_active_ordered_by_price(self) -> list[CreditPackage]:
        """Get active packages ordered by price ascending."""
        stmt = (
            select(CreditPackage)
            .where(CreditPackage.is_active == True)  # noqa: E712
            .order_by(CreditPackage.fiat_price.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
