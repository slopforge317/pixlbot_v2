"""
Script for manually adding credits to a user account.

Usage:
    PYTHONPATH=app poetry run python scripts/add_credits.py \
        --id <telegram_user_id> --credits <amount>

Examples:
    PYTHONPATH=app poetry run python scripts/add_credits.py --id 123456789 --credits 100
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add app to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "app"))

from db.enums import TransactionType  # noqa: E402
from db.models.transaction import Transaction  # noqa: E402
from db.repositories.user import UserRepository  # noqa: E402
from db.session import async_session_maker, engine  # noqa: E402


async def add_credits(telegram_user_id: int, credits: int) -> None:
    """Add credits to user account."""
    async with async_session_maker() as session:
        user_repo = UserRepository(session)

        # Find user
        user = await user_repo.get_by_telegram_id(telegram_user_id)
        if not user:
            print(f"Error: User with Telegram ID {telegram_user_id} not found")
            sys.exit(1)

        # Get balance before
        balance_before = await user_repo.get_balance(user.user_id)

        # Create manual transaction
        transaction = Transaction(
            user_id=user.user_id,
            type=TransactionType.manual,
            amount_credits=credits,
        )
        session.add(transaction)
        await session.commit()

        # Get balance after
        balance_after = await user_repo.get_balance(user.user_id)

        print(f"User: {user.first_name} (@{user.username or 'no username'})")
        print(f"Telegram ID: {telegram_user_id}")
        print(f"Credits added: {credits}")
        print(f"Balance before: {balance_before}")
        print(f"Balance after: {balance_after}")
        print(f"Transaction ID: {transaction.tx_id}")
        print("\nCredits added successfully!")


async def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Manually add credits to a user account"
    )
    parser.add_argument(
        "--id",
        type=int,
        required=True,
        help="Telegram user ID",
    )
    parser.add_argument(
        "--credits",
        type=int,
        required=True,
        help="Number of credits to add (positive number)",
    )

    args = parser.parse_args()

    if args.credits <= 0:
        print("Error: Credits must be a positive number")
        sys.exit(1)

    await add_credits(args.id, args.credits)

    # Close database connections
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
