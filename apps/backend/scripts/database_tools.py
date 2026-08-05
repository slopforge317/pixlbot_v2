"""Explicit maintenance commands for the restored test database."""

import argparse
import asyncio
import sys
from pathlib import Path

from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).parent.parent / "app"))

from db.session import engine  # noqa: E402

SANITIZE_CONFIRMATION = "SANITIZE_LEGACY_TEST_DATA"

SUMMARY_TABLES = (
    "users",
    "providers",
    "ai_models",
    "pricing_variants",
    "credit_packages",
    "generations_job",
    "transactions",
    "payments",
    "funnel_steps",
    "scheduled_messages",
)


async def sanitize(confirmation: str) -> int:
    if confirmation != SANITIZE_CONFIRMATION:
        print(f"Refusing sanitization: pass --confirm {SANITIZE_CONFIRMATION}")
        return 4

    async with engine.begin() as connection:
        messages = await connection.execute(
            text(
                "UPDATE scheduled_messages "
                "SET status = 'cancelled' "
                "WHERE status = 'pending'"
            )
        )
        funnels = await connection.execute(
            text("UPDATE funnel_steps SET is_active = false WHERE is_active = true")
        )

    print(f"Cancelled scheduled messages: {messages.rowcount}")
    print(f"Disabled funnel steps: {funnels.rowcount}")
    return 0


async def summary() -> int:
    async with engine.connect() as connection:
        revision_result = await connection.execute(
            text("SELECT version_num FROM alembic_version")
        )
        print(
            "Alembic revision: "
            f"{revision_result.scalar_one_or_none() or '<missing>'}"
        )
        for table_name in SUMMARY_TABLES:
            result = await connection.execute(
                text(f'SELECT count(*) FROM "{table_name}"')
            )
            print(f"{table_name}: {result.scalar_one()}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    sanitize_parser = subparsers.add_parser("sanitize")
    sanitize_parser.add_argument("--confirm", default="")

    subparsers.add_parser("summary")
    return parser.parse_args()


async def async_main() -> int:
    args = parse_args()
    try:
        if args.command == "sanitize":
            return await sanitize(args.confirm)
        return await summary()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(async_main()))
