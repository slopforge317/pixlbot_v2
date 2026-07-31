"""Validate and adopt the legacy database for the new Alembic baseline.

This script is intentionally explicit. It never changes the revision or test data
unless the matching confirmation value is supplied on the command line.
"""

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext

sys.path.insert(0, str(Path(__file__).parent.parent / "app"))

import db.models  # noqa: E402, F401 — registers models in Base.metadata
from db.base import Base  # noqa: E402
from db.session import engine  # noqa: E402

EXPECTED_LEGACY_REVISION = "f7d735a7befd"
NEW_BASELINE_REVISION = "20260727_0001"
ADOPT_CONFIRMATION = "ADOPT_LEGACY_SCHEMA"
SANITIZE_CONFIRMATION = "SANITIZE_LEGACY_TEST_DATA"
RECONCILE_CONFIRMATION = "RECONCILE_LEGACY_ENUMS"

LEGACY_ENUM_COLUMNS = (
    ("funnel_steps", "trigger_event", "funneltriggerevent", 21),
    ("funnel_steps", "condition", "funnelcondition", 18),
    ("scheduled_messages", "status", "scheduledmessagestatus", 9),
)

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


def _compare_schema(connection: Connection) -> list[Any]:
    context = MigrationContext.configure(
        connection,
        opts={
            "compare_type": True,
            "compare_server_default": True,
        },
    )
    return list(compare_metadata(context, Base.metadata))


async def _get_revision() -> str | None:
    async with engine.connect() as connection:
        result = await connection.execute(
            text("SELECT version_num FROM alembic_version")
        )
        return result.scalar_one_or_none()


async def _get_schema_diff() -> list[Any]:
    async with engine.connect() as connection:
        return await connection.run_sync(_compare_schema)


def _print_diff(diffs: list[Any]) -> None:
    if not diffs:
        print("Schema diff: empty")
        return

    print(f"Schema diff: {len(diffs)} change(s)")
    for index, diff in enumerate(diffs, start=1):
        print(f"  {index}. {diff!r}")


async def check(expected_revision: str) -> int:
    revision = await _get_revision()
    print(f"Current legacy revision: {revision or '<missing>'}")
    print(f"Expected legacy revision: {expected_revision}")

    diffs = await _get_schema_diff()
    _print_diff(diffs)

    if revision != expected_revision:
        print("Refusing adoption: unexpected Alembic revision.")
        return 2
    if diffs:
        print("Refusing adoption: database schema differs from ORM metadata.")
        return 3

    print("Legacy database is compatible with the new baseline.")
    return 0


async def adopt(expected_revision: str, confirmation: str) -> int:
    if confirmation != ADOPT_CONFIRMATION:
        print(f"Refusing adoption: pass --confirm {ADOPT_CONFIRMATION}")
        return 4

    async with engine.begin() as connection:
        result = await connection.execute(
            text("SELECT version_num FROM alembic_version FOR UPDATE")
        )
        revision = result.scalar_one_or_none()
        diffs = await connection.run_sync(_compare_schema)

        print(f"Current legacy revision: {revision or '<missing>'}")
        _print_diff(diffs)

        if revision != expected_revision:
            print("Refusing adoption: unexpected Alembic revision.")
            return 2
        if diffs:
            print("Refusing adoption: database schema differs from ORM metadata.")
            return 3

        await connection.execute(text("DELETE FROM alembic_version"))
        await connection.execute(
            text("INSERT INTO alembic_version (version_num) VALUES (:revision)"),
            {"revision": NEW_BASELINE_REVISION},
        )

    print(f"Alembic baseline adopted: {NEW_BASELINE_REVISION}")
    return 0


async def reconcile_enums(expected_revision: str, confirmation: str) -> int:
    if confirmation != RECONCILE_CONFIRMATION:
        print(f"Refusing reconciliation: pass --confirm {RECONCILE_CONFIRMATION}")
        return 4

    async with engine.begin() as connection:
        result = await connection.execute(
            text("SELECT version_num FROM alembic_version FOR UPDATE")
        )
        revision = result.scalar_one_or_none()
        if revision != expected_revision:
            print(
                "Refusing reconciliation: expected revision "
                f"{expected_revision}, found {revision or '<missing>'}."
            )
            return 2

        for table_name, column_name, enum_name, varchar_length in LEGACY_ENUM_COLUMNS:
            type_result = await connection.execute(
                text(
                    "SELECT data_type, udt_name "
                    "FROM information_schema.columns "
                    "WHERE table_schema = 'public' "
                    "AND table_name = :table_name "
                    "AND column_name = :column_name"
                ),
                {"table_name": table_name, "column_name": column_name},
            )
            column_type = type_result.one_or_none()
            if column_type is None:
                print(f"Refusing reconciliation: missing {table_name}.{column_name}.")
                return 5

            data_type, udt_name = column_type
            if data_type == "character varying":
                print(f"Already reconciled: {table_name}.{column_name}")
                continue
            if data_type != "USER-DEFINED" or udt_name != enum_name:
                print(
                    "Refusing reconciliation: unexpected type for "
                    f"{table_name}.{column_name}: {data_type}/{udt_name}."
                )
                return 5

            await connection.execute(
                text(
                    f'ALTER TABLE "{table_name}" '
                    f'ALTER COLUMN "{column_name}" '
                    f"TYPE VARCHAR({varchar_length}) "
                    f'USING "{column_name}"::text'
                )
            )
            print(
                f"Converted {table_name}.{column_name}: "
                f"{enum_name} -> VARCHAR({varchar_length})"
            )

        for enum_name in sorted({item[2] for item in LEGACY_ENUM_COLUMNS}):
            await connection.execute(text(f'DROP TYPE IF EXISTS "{enum_name}"'))
            print(f"Dropped legacy enum type: {enum_name}")

        diffs = await connection.run_sync(_compare_schema)
        _print_diff(diffs)
        if diffs:
            print("Reconciliation rolled back: schema diff is still not empty.")
            await connection.rollback()
            return 3

    print("Legacy enum reconciliation completed successfully.")
    return 0


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

    check_parser = subparsers.add_parser("check")
    check_parser.add_argument(
        "--expected-revision",
        default=EXPECTED_LEGACY_REVISION,
    )

    adopt_parser = subparsers.add_parser("adopt")
    adopt_parser.add_argument(
        "--expected-revision",
        default=EXPECTED_LEGACY_REVISION,
    )
    adopt_parser.add_argument("--confirm", default="")

    reconcile_parser = subparsers.add_parser("reconcile-enums")
    reconcile_parser.add_argument(
        "--expected-revision",
        default=EXPECTED_LEGACY_REVISION,
    )
    reconcile_parser.add_argument("--confirm", default="")

    sanitize_parser = subparsers.add_parser("sanitize")
    sanitize_parser.add_argument("--confirm", default="")

    subparsers.add_parser("summary")
    return parser.parse_args()


async def async_main() -> int:
    args = parse_args()
    try:
        if args.command == "check":
            return await check(args.expected_revision)
        if args.command == "adopt":
            return await adopt(args.expected_revision, args.confirm)
        if args.command == "reconcile-enums":
            return await reconcile_enums(args.expected_revision, args.confirm)
        if args.command == "sanitize":
            return await sanitize(args.confirm)
        return await summary()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(async_main()))
