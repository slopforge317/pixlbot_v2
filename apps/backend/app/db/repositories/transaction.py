from db.enums import TransactionType
from db.models.transaction import Transaction
from db.repositories.base import BaseRepository
from loguru import logger
from sqlalchemy import select


class TransactionRepository(BaseRepository[Transaction]):
    """Repository for Transaction operations.

    Note: Transactions table is an immutable ledger.
    Use create_* methods instead of update/delete.
    """

    model = Transaction

    async def get_user_transactions(
        self, user_id: int, limit: int = 50, offset: int = 0
    ) -> list[Transaction]:
        """Get user's transaction history, newest first."""
        stmt = (
            select(Transaction)
            .where(Transaction.user_id == user_id)
            .order_by(Transaction.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_type(
        self, user_id: int, tx_type: TransactionType
    ) -> list[Transaction]:
        """Get user's transactions filtered by type."""
        stmt = (
            select(Transaction)
            .where(Transaction.user_id == user_id, Transaction.type == tx_type)
            .order_by(Transaction.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create_deposit(
        self,
        user_id: int,
        amount_credits: int,
        payment_id: int | None = None,
        credit_package_id: int | None = None,
    ) -> Transaction:
        """Create a deposit (credit purchase) transaction."""
        tx = await self.create(
            user_id=user_id,
            type=TransactionType.deposit,
            amount_credits=abs(amount_credits),
            payment_id=payment_id,
            credit_package_id=credit_package_id,
        )
        logger.info(
            f"Transaction created: type=deposit, user_id={user_id}, "
            f"amount={abs(amount_credits)}, payment_id={payment_id}"
        )
        return tx

    async def create_withdrawal(
        self,
        user_id: int,
        amount_credits: int,
        job_id: int,
    ) -> Transaction:
        """Create a withdrawal (generation charge) transaction.

        The amount will be stored as negative.
        """
        tx = await self.create(
            user_id=user_id,
            type=TransactionType.withdrawal,
            amount_credits=-abs(amount_credits),
            job_id=job_id,
        )
        logger.info(
            f"Transaction created: type=withdrawal, user_id={user_id}, "
            f"amount={-abs(amount_credits)}, job_id={job_id}"
        )
        return tx

    async def create_refund(
        self,
        user_id: int,
        amount_credits: int,
        job_id: int,
    ) -> Transaction:
        """Create a refund transaction (e.g., failed generation)."""
        tx = await self.create(
            user_id=user_id,
            type=TransactionType.refund,
            amount_credits=abs(amount_credits),
            job_id=job_id,
        )
        logger.info(
            f"Transaction created: type=refund, user_id={user_id}, "
            f"amount={abs(amount_credits)}, job_id={job_id}"
        )
        return tx

    async def create_bonus(
        self,
        user_id: int,
        amount_credits: int,
    ) -> Transaction:
        """Create a bonus transaction (e.g., welcome bonus)."""
        tx = await self.create(
            user_id=user_id,
            type=TransactionType.bonus,
            amount_credits=abs(amount_credits),
        )
        logger.info(
            f"Transaction created: type=bonus, user_id={user_id}, "
            f"amount={abs(amount_credits)}"
        )
        return tx
