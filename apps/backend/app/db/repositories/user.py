from core.logging import log_repository
from db.models.transaction import Transaction
from db.models.user import User
from db.repositories.base import BaseRepository
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert


class UserRepository(BaseRepository[User]):
    """Repository for User operations."""

    model = User

    @log_repository
    async def get_by_telegram_id(self, telegram_user_id: int) -> User | None:
        """Get user by Telegram ID."""
        stmt = select(User).where(User.telegram_user_id == telegram_user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    @log_repository
    async def get_or_create(
        self,
        telegram_user_id: int,
        chat_id: int,
        first_name: str,
        last_name: str | None = None,
        username: str | None = None,
        utm_source: str = "direct",
    ) -> tuple[User, bool]:
        """Get existing user or create new one.

        Uses INSERT ON CONFLICT DO NOTHING to avoid IntegrityError and
        transaction rollback on concurrent requests for the same user.

        Returns:
            Tuple of (user, created) where created is True if user was created.
        """
        user = await self.get_by_telegram_id(telegram_user_id)
        if user:
            return user, False

        stmt = (
            pg_insert(User)
            .values(
                telegram_user_id=telegram_user_id,
                chat_id=chat_id,
                first_name=first_name,
                last_name=last_name,
                username=username,
                utm_source=utm_source,
            )
            .on_conflict_do_nothing(index_elements=["telegram_user_id"])
        )
        result = await self.session.execute(stmt)
        created = result.rowcount > 0

        user = await self.get_by_telegram_id(telegram_user_id)
        if user is None:
            raise RuntimeError("User not found after get_or_create")
        return user, created

    @log_repository
    async def get_balance(self, user_id: int) -> int:
        """Get user's credit balance (sum of all transactions)."""
        stmt = select(func.coalesce(func.sum(Transaction.amount_credits), 0)).where(
            Transaction.user_id == user_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()
