"""
Seed script for loading credit packages into the database.

Uses upsert logic: updates existing rows and creates new ones.
Never deletes — safe for production (payments/transactions reference packages).

Usage:
    PYTHONPATH=app poetry run python scripts/seed_packages.py
"""

import asyncio
import sys
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import select

# Add app to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "app"))

from db.models.credit_package import CreditPackage  # noqa: E402
from db.session import async_session_maker, create_tables, engine  # noqa: E402


def load_packages() -> list[dict[str, Any]]:
    """Load credit packages from YAML file."""
    yaml_file = Path(__file__).parent / "seed_packages.yaml"
    if not yaml_file.exists():
        raise FileNotFoundError(f"Packages file not found: {yaml_file}")

    with open(yaml_file, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    return data


async def main() -> None:
    """Main entry point for the seed script."""
    from core.config import settings

    print(f"Database: {settings.database_url}")

    print("Loading packages from YAML...")
    packages = load_packages()

    print("Creating tables if needed...")
    await create_tables()

    print("Seeding credit packages...")
    async with async_session_maker() as session:
        # Load all existing packages
        result = await session.execute(select(CreditPackage))
        existing = {cp.name: cp for cp in result.scalars().all()}

        seen_names: set[str] = set()

        for pkg in packages:
            name = pkg["name"]
            seen_names.add(name)

            if name in existing:
                cp = existing[name]
                cp.description = pkg["description"]
                cp.credit_amount = pkg["credit_amount"]
                cp.fiat_price = pkg["fiat_price"]
                cp.is_active = True
                print(f"  Updated package: {name} ({pkg['credit_amount']} credits)")
            else:
                cp = CreditPackage(
                    name=name,
                    description=pkg["description"],
                    credit_amount=pkg["credit_amount"],
                    fiat_price=pkg["fiat_price"],
                )
                session.add(cp)
                print(f"  Created package: {name} ({pkg['credit_amount']} credits)")

        # Deactivate packages not in YAML
        for name, cp in existing.items():
            if name not in seen_names and cp.is_active:
                cp.is_active = False
                print(f"  Deactivated stale package: {name}")

        await session.commit()

    print("\nSeed completed successfully!")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
