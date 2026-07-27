from typing import Any, Generic, TypeVar

from db.base import Base, TimestampMixin
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """Base repository with generic CRUD operations."""

    model: type[ModelT]

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, id: int) -> ModelT | None:
        """Get entity by primary key."""
        return await self.session.get(self.model, id)

    async def get_all(self, limit: int = 100, offset: int = 0) -> list[ModelT]:
        """Get all entities with pagination."""
        stmt = select(self.model).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, **kwargs: Any) -> ModelT:
        """Create new entity."""
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        if issubclass(self.model, TimestampMixin):
            await self.session.refresh(instance, attribute_names=["created_at"])
        return instance

    async def update(self, instance: ModelT, **kwargs: Any) -> ModelT:
        """Update entity attributes."""
        for key, value in kwargs.items():
            setattr(instance, key, value)
        await self.session.flush()
        return instance

    async def delete(self, instance: ModelT) -> None:
        """Delete entity."""
        await self.session.delete(instance)
        await self.session.flush()
