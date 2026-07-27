"""
Seed script for loading providers, AI models, and pricing variants into the database.

Uses upsert logic: updates existing rows and creates new ones.
Never deletes transactions or generation_jobs — safe for production.

Usage:
    PYTHONPATH=app poetry run python scripts/seed_db.py
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import select

# Add app to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "app"))

from db.models.ai_model import AIModel  # noqa: E402
from db.models.pricing_variant import PricingVariant  # noqa: E402
from db.models.provider import Provider  # noqa: E402
from db.session import async_session_maker, engine  # noqa: E402


def load_api_parameters() -> list[dict[str, Any]]:
    """Load API parameters from YAML file."""
    yaml_file = Path(__file__).parent / "api_parameters.yaml"
    if not yaml_file.exists():
        raise FileNotFoundError(f"API parameters file not found: {yaml_file}")

    with open(yaml_file, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    return data.get("providers", [])


def load_seed_prices() -> dict[str, list[dict[str, Any]]]:
    """Load pricing data from YAML file (flat list grouped by product)."""
    yaml_file = Path(__file__).parent / "seed_prices.yaml"
    if not yaml_file.exists():
        raise FileNotFoundError(f"Seed prices file not found: {yaml_file}")

    with open(yaml_file, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    # Convert flat list to dict keyed by product (api_model_id)
    prices: dict[str, list[dict[str, Any]]] = {}
    for entry in data:
        product = entry["product"]
        if product not in prices:
            prices[product] = []
        prices[product].append(
            {
                "variant_values": entry.get("variant_values", {}),
                "price": entry["price"],
                "active": entry.get("active", True),
            }
        )
    return prices


def extract_variant_keys(parameters: dict[str, Any]) -> list[str]:
    """Extract parameter keys with variant: true from input parameters."""
    variant_keys: list[str] = []
    for key, spec in parameters.items():
        if isinstance(spec, dict) and spec.get("variant") is True:
            variant_keys.append(key)
    return variant_keys


async def upsert_provider(
    session: Any, title: str, gen_type: str, sort_order: int = 0
) -> Provider:
    """Get existing provider by title or create a new one."""
    result = await session.execute(select(Provider).where(Provider.title == title))
    provider = result.scalar_one_or_none()

    if provider:
        provider.gen_type = gen_type
        provider.active = True
        provider.sort_order = sort_order
        print(f"Updated provider: {title} ({gen_type}, sort_order={sort_order})")
    else:
        provider = Provider(
            title=title, gen_type=gen_type, active=True, sort_order=sort_order
        )
        session.add(provider)
        await session.flush()
        print(f"Created provider: {title} ({gen_type}, sort_order={sort_order})")

    return provider


async def upsert_model(
    session: Any,
    provider_id: int,
    api_model_id: str,
    title: str,
    input_schema: dict[str, Any],
    variant_keys: list[str],
    sort_order: int = 0,
    status: str | None = None,
) -> AIModel:
    """Get existing model by api_model_id or create a new one."""
    result = await session.execute(
        select(AIModel).where(AIModel.api_model_id == api_model_id)
    )
    model = result.scalar_one_or_none()

    if model:
        model.provider_id = provider_id
        model.title = title
        model.input_schema = input_schema
        model.variant_keys = variant_keys
        model.active = True
        model.sort_order = sort_order
        model.status = status
        print(f"  Updated model: {api_model_id} ({title}, sort_order={sort_order})")
    else:
        model = AIModel(
            provider_id=provider_id,
            api_model_id=api_model_id,
            title=title,
            input_schema=input_schema,
            variant_keys=variant_keys,
            active=True,
            sort_order=sort_order,
            status=status,
        )
        session.add(model)
        await session.flush()
        print(f"  Created model: {api_model_id} ({title}, sort_order={sort_order})")

    return model


async def upsert_pricing_variants(
    session: Any,
    model_id: int,
    pricing_data: list[dict[str, Any]],
) -> None:
    """Upsert pricing variants for a model. Deactivate stale ones."""
    # Load existing variants for this model
    result = await session.execute(
        select(PricingVariant).where(PricingVariant.model_id == model_id)
    )
    existing = list(result.scalars().all())

    # Index existing by serialized variant_values for matching
    existing_map: dict[str, PricingVariant] = {}
    for pv in existing:
        key = json.dumps(pv.variant_values, sort_keys=True)
        existing_map[key] = pv

    seen_keys: set[str] = set()

    for pv_data in pricing_data:
        key = json.dumps(pv_data["variant_values"], sort_keys=True)
        seen_keys.add(key)

        if key in existing_map:
            pv = existing_map[key]
            pv.price = pv_data["price"]
            pv.active = pv_data.get("active", True)
            print(
                f"    Updated pricing: {pv_data['variant_values']} "
                f"= {pv_data['price']} credits"
            )
        else:
            pv = PricingVariant(
                model_id=model_id,
                variant_values=pv_data["variant_values"],
                price=pv_data["price"],
                active=pv_data.get("active", True),
            )
            session.add(pv)
            print(
                f"    Created pricing: {pv_data['variant_values']} "
                f"= {pv_data['price']} credits"
            )

    # Deactivate variants not in the seed data
    for key, pv in existing_map.items():
        if key not in seen_keys and pv.active:
            pv.active = False
            print(f"    Deactivated stale pricing: {pv.variant_values}")


async def seed_data(
    api_params: list[dict[str, Any]],
    prices: dict[str, list[dict[str, Any]]],
) -> None:
    """Seed providers, models, and pricing variants using upsert logic."""
    async with async_session_maker() as session:
        # Track providers by title to deduplicate within YAML
        provider_cache: dict[str, Provider] = {}

        # Track model sort_order per provider
        provider_model_counter: dict[str, int] = {}

        for entry in api_params:
            provider_title = entry["provider"]
            gen_type = entry["gen_type"]
            model_values = entry["model"]["values"]
            model_ui_label = entry["model"]["ui_label"]
            input_params = entry["input"]["parameters"]
            provider_sort_order = entry.get("sort_order", 0)
            model_sort_order = entry["model"].get("sort_order", 0)
            status = entry.get("status")

            # Upsert provider
            if provider_title not in provider_cache:
                provider = await upsert_provider(
                    session, provider_title, gen_type, provider_sort_order
                )
                provider_cache[provider_title] = provider
            else:
                provider = provider_cache[provider_title]

            # Compute model sort_order: use explicit value or fallback to counter
            if model_sort_order == 0:
                counter = provider_model_counter.get(provider_title, 0)
                counter += 1
                provider_model_counter[provider_title] = counter
                effective_model_sort_order = counter
            else:
                effective_model_sort_order = model_sort_order

            # Extract variant_keys and input_schema
            variant_keys = extract_variant_keys(input_params)
            input_schema = input_params

            # Upsert model for each api_model_id
            for api_model_id in model_values:
                model = await upsert_model(
                    session,
                    provider_id=provider.id,
                    api_model_id=api_model_id,
                    title=model_ui_label,
                    input_schema=input_schema,
                    variant_keys=variant_keys,
                    sort_order=effective_model_sort_order,
                    status=status,
                )

                # Upsert pricing variants
                model_prices = prices.get(api_model_id, [])
                if not model_prices:
                    print(f"    WARNING: No pricing found for {api_model_id}")
                    continue

                await upsert_pricing_variants(session, model.id, model_prices)

        await session.commit()
        print("\nSeed completed successfully!")


async def main() -> None:
    """Main entry point for the seed script."""
    from core.config import settings

    print(f"Database: {settings.database_url}")

    print("Loading API parameters...")
    api_params = load_api_parameters()

    print("Loading seed prices...")
    prices = load_seed_prices()

    print("Seeding providers, models, and pricing variants...")
    await seed_data(api_params, prices)

    # Close database connections
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
