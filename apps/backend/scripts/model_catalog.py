"""Validate and manage the declarative model catalog.

Usage from apps/backend:
    PYTHONPATH=app poetry run python scripts/model_catalog.py validate
    PYTHONPATH=app poetry run python scripts/model_catalog.py list
    PYTHONPATH=app poetry run python scripts/model_catalog.py show gpt-image-2
    PYTHONPATH=app poetry run python scripts/model_catalog.py diff
    PYTHONPATH=app poetry run python scripts/model_catalog.py seed
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

SCRIPT_DIR = Path(__file__).parent
DEFAULT_CATALOG_DIR = SCRIPT_DIR.parent / "catalog" / "models"
VALID_INPUT_MODES = {"text_only", "image_required", "image_optional"}


class CatalogPrice(BaseModel):
    """A single credit price for one set of variant values."""

    model_config = ConfigDict(extra="forbid")

    variant_values: dict[str, Any] = Field(default_factory=dict)
    price: int = Field(gt=0)
    active: bool = True


class CatalogImplementation(BaseModel):
    """One provider API implementation of a public model."""

    model_config = ConfigDict(extra="forbid")

    api_model_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    input_mode: Literal["text_only", "image_required", "image_optional"]
    sort_order: int = Field(default=0, ge=0)
    status: str | None = None
    parameters: dict[str, dict[str, Any]]
    pricing: list[CatalogPrice] = Field(min_length=1)


class CatalogModel(BaseModel):
    """A public model family shown as one item in the TMA."""

    model_config = ConfigDict(extra="forbid")

    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    title: str = Field(min_length=1)
    gen_type: Literal["image", "video"] = "image"
    active: bool = True
    sort_order: int = Field(default=0, ge=0)
    source: list[str] = Field(default_factory=list)
    implementations: list[CatalogImplementation] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_implementations(self) -> "CatalogModel":
        ids = [item.api_model_id for item in self.implementations]
        if len(ids) != len(set(ids)):
            raise ValueError(f"duplicate api_model_id in {self.slug!r}")

        if self.active and self.gen_type != "image":
            raise ValueError(f"active model {self.slug!r} must have gen_type=image")

        for item in self.implementations:
            if not self.active:
                continue

            variant_keys = {
                key
                for key, spec in item.parameters.items()
                if spec.get("variant") is True
            }
            for price in item.pricing:
                price_keys = set(price.variant_values)
                if price_keys != variant_keys:
                    raise ValueError(
                        f"pricing keys for {item.api_model_id!r} are "
                        f"{sorted(price_keys)}, expected {sorted(variant_keys)}"
                    )

            arrays = [
                spec for spec in item.parameters.values() if spec.get("type") == "array"
            ]
            required_arrays = [spec for spec in arrays if spec.get("required")]
            if item.input_mode == "text_only" and required_arrays:
                raise ValueError(
                    f"text_only model {item.api_model_id!r} needs no image"
                )
            if item.input_mode == "image_required" and len(required_arrays) != 1:
                raise ValueError(
                    "image_required model "
                    f"{item.api_model_id!r} needs one required array"
                )
            for spec in arrays:
                if not isinstance(spec.get("max_images"), int):
                    raise ValueError(f"array in {item.api_model_id!r} needs max_images")
                if not isinstance(spec.get("max_image_size_mb"), int):
                    raise ValueError(
                        f"array in {item.api_model_id!r} needs max_image_size_mb"
                    )

        return self


def extract_variant_keys(parameters: dict[str, Any]) -> list[str]:
    """Return pricing dimensions in declaration order."""
    return [
        key
        for key, spec in parameters.items()
        if isinstance(spec, dict) and spec.get("variant") is True
    ]


def normalize_input_schema(parameters: dict[str, Any]) -> dict[str, Any]:
    """Build frontend schema with stable field and option ordering."""
    normalized = deepcopy(parameters)
    for spec in normalized.values():
        if not isinstance(spec, dict):
            continue
        ui_order = spec.get("ui_order")
        if isinstance(ui_order, int) and 0 < ui_order < 10:
            spec["ui_order"] = ui_order * 10

        values = spec.pop("values", None)
        if not isinstance(values, list):
            continue
        options: list[dict[str, Any]] = []
        for index, value in enumerate(values, start=1):
            if isinstance(value, dict):
                option = dict(value)
                option.setdefault("label", str(option["value"]))
                option.setdefault("sort_order", index * 10)
            else:
                option = {
                    "value": value,
                    "label": str(value),
                    "sort_order": index * 10,
                }
            options.append(option)
        spec["options"] = sorted(
            options, key=lambda option: (option["sort_order"], str(option["value"]))
        )
    return normalized


def load_catalog(catalog_dir: Path = DEFAULT_CATALOG_DIR) -> list[CatalogModel]:
    """Load, type-check, and cross-check all catalog files."""
    if not catalog_dir.exists():
        raise FileNotFoundError(f"Catalog directory not found: {catalog_dir}")

    models: list[CatalogModel] = []
    slugs: set[str] = set()
    api_model_ids: set[str] = set()
    for path in sorted(catalog_dir.glob("*.yaml")):
        with path.open(encoding="utf-8") as stream:
            model = CatalogModel.model_validate(yaml.safe_load(stream))
        if path.stem != model.slug:
            raise ValueError(f"File {path.name!r} must match slug {model.slug!r}")
        if model.slug in slugs:
            raise ValueError(f"Duplicate slug {model.slug!r}")
        slugs.add(model.slug)
        for implementation in model.implementations:
            if implementation.api_model_id in api_model_ids:
                raise ValueError(
                    f"Duplicate api_model_id {implementation.api_model_id!r}"
                )
            api_model_ids.add(implementation.api_model_id)
        models.append(model)

    if not models:
        raise ValueError(f"Catalog has no YAML files: {catalog_dir}")
    return sorted(models, key=lambda item: (item.sort_order, item.slug))


def catalog_to_seed_data(
    models: list[CatalogModel],
) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    """Convert typed catalog files into the existing idempotent seed format."""
    api_params: list[dict[str, Any]] = []
    prices: dict[str, list[dict[str, Any]]] = {}
    for model in models:
        for implementation in sorted(
            model.implementations, key=lambda item: (item.sort_order, item.api_model_id)
        ):
            entry: dict[str, Any] = {
                "provider": model.title,
                "slug": model.slug,
                "sort_order": model.sort_order,
                "active": model.active,
                "model": {
                    "type": "string",
                    "required": True,
                    "input_mode": implementation.input_mode,
                    "values": [implementation.api_model_id],
                    "ui_label": implementation.title,
                    "sort_order": implementation.sort_order,
                },
                "input": {
                    "type": "object",
                    "required": True,
                    "parameters": implementation.parameters,
                },
                "callBackUrl": {"type": "string", "required": False},
                "gen_type": model.gen_type,
            }
            if implementation.status is not None:
                entry["status"] = implementation.status
            api_params.append(entry)
            prices[implementation.api_model_id] = [
                price.model_dump() for price in implementation.pricing
            ]
    return api_params, prices


def load_seed_data(
    catalog_dir: Path = DEFAULT_CATALOG_DIR,
) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    return catalog_to_seed_data(load_catalog(catalog_dir))


def _dump_model(model: CatalogModel) -> str:
    return yaml.safe_dump(
        model.model_dump(exclude_defaults=True, exclude_none=True),
        allow_unicode=True,
        sort_keys=False,
    )


def import_legacy(
    parameters_path: Path,
    prices_path: Path,
    output_dir: Path,
    force: bool,
) -> None:
    """Split the former monolithic files into one file per public model."""
    with parameters_path.open(encoding="utf-8") as stream:
        entries = yaml.safe_load(stream).get("providers", [])
    with prices_path.open(encoding="utf-8") as stream:
        raw_prices = yaml.safe_load(stream)

    prices_by_product: dict[str, list[dict[str, Any]]] = {}
    for price in raw_prices:
        prices_by_product.setdefault(price["product"], []).append(
            {
                "variant_values": price.get("variant_values", {}),
                "price": price["price"],
                "active": price.get("active", True),
            }
        )

    grouped: dict[str, dict[str, Any]] = {}
    for entry in entries:
        slug = entry["slug"]
        family = grouped.setdefault(
            slug,
            {
                "slug": slug,
                "title": entry["provider"],
                "gen_type": entry["gen_type"],
                "active": entry.get("active", entry["gen_type"] == "image"),
                "sort_order": entry.get("sort_order", 0),
                "implementations": [],
            },
        )
        for api_model_id in entry["model"]["values"]:
            implementation = {
                "api_model_id": api_model_id,
                "title": entry["model"]["ui_label"],
                "input_mode": entry["model"]["input_mode"],
                "sort_order": entry["model"].get("sort_order", 0),
                "parameters": entry["input"]["parameters"],
                "pricing": prices_by_product.get(api_model_id, []),
            }
            if entry.get("status") is not None:
                implementation["status"] = entry["status"]
            family["implementations"].append(implementation)

    output_dir.mkdir(parents=True, exist_ok=True)
    for slug, raw_model in grouped.items():
        path = output_dir / f"{slug}.yaml"
        if path.exists() and not force:
            raise FileExistsError(f"Refusing to overwrite {path}; pass --force")
        model = CatalogModel.model_validate(raw_model)
        path.write_text(_dump_model(model), encoding="utf-8")
    print(f"Imported {len(grouped)} public models into {output_dir}")


async def show_diff(models: list[CatalogModel]) -> None:
    """Print database rows that seed would create or update."""
    sys.path.insert(0, str(SCRIPT_DIR.parent / "app"))
    from db.models.ai_model import AIModel
    from db.models.provider import Provider
    from db.session import async_session_maker, engine
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    changes: list[str] = []
    async with async_session_maker() as session:
        result = await session.execute(
            select(Provider).options(
                selectinload(Provider.models).selectinload(AIModel.pricing_variants)
            )
        )
        existing = {provider.slug: provider for provider in result.scalars().unique()}
        desired_slugs = {family.slug for family in models}
        for slug, provider in existing.items():
            if slug not in desired_slugs and provider.active:
                changes.append(f"- deactivate provider {slug}")
        for family in models:
            provider = existing.get(family.slug)
            if provider is None:
                changes.append(f"+ provider {family.slug}")
                for item in family.implementations:
                    changes.append(f"  + model {item.api_model_id}")
                continue
            provider_state = (
                provider.title,
                provider.gen_type,
                provider.active,
                provider.sort_order,
            )
            desired_provider_state = (
                family.title,
                family.gen_type,
                family.active,
                family.sort_order,
            )
            if provider_state != desired_provider_state:
                changes.append(f"~ provider {family.slug}")

            current_models = {item.api_model_id: item for item in provider.models}
            desired_model_ids = {item.api_model_id for item in family.implementations}
            for api_model_id, current in current_models.items():
                if api_model_id not in desired_model_ids and current.active:
                    changes.append(f"  - deactivate model {api_model_id}")
            for item in family.implementations:
                current = current_models.get(item.api_model_id)
                if current is None:
                    changes.append(f"  + model {item.api_model_id}")
                    continue
                desired_schema = normalize_input_schema(item.parameters)
                desired_keys = extract_variant_keys(item.parameters)
                model_state = (
                    current.title,
                    current.input_mode,
                    current.input_schema,
                    current.variant_keys,
                    current.active,
                    current.sort_order,
                    current.status,
                )
                desired_model_state = (
                    item.title,
                    item.input_mode,
                    desired_schema,
                    desired_keys,
                    family.active,
                    item.sort_order,
                    item.status,
                )
                if model_state != desired_model_state:
                    changes.append(f"  ~ model {item.api_model_id}")

                current_prices = {
                    json.dumps(price.variant_values, sort_keys=True): (
                        price.price,
                        price.active,
                    )
                    for price in current.pricing_variants
                }
                desired_prices = {
                    json.dumps(price.variant_values, sort_keys=True): (
                        price.price,
                        price.active,
                    )
                    for price in item.pricing
                }
                if current_prices != desired_prices:
                    changes.append(f"    ~ pricing {item.api_model_id}")
    await engine.dispose()
    print("\n".join(changes) if changes else "Catalog matches database")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog-dir", type=Path, default=DEFAULT_CATALOG_DIR)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("validate")
    subparsers.add_parser("list")
    show = subparsers.add_parser("show")
    show.add_argument("slug")
    subparsers.add_parser("diff")
    subparsers.add_parser("seed")
    legacy = subparsers.add_parser("import-legacy")
    legacy.add_argument("--parameters", type=Path, required=True)
    legacy.add_argument("--prices", type=Path, required=True)
    legacy.add_argument("--output", type=Path, default=DEFAULT_CATALOG_DIR)
    legacy.add_argument("--force", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "import-legacy":
        import_legacy(args.parameters, args.prices, args.output, args.force)
        return

    models = load_catalog(args.catalog_dir)
    implementations = sum(len(model.implementations) for model in models)
    prices = sum(
        len(item.pricing) for model in models for item in model.implementations
    )
    if args.command == "validate":
        print(
            f"Catalog valid: {len(models)} public models, "
            f"{implementations} implementations, {prices} prices"
        )
    elif args.command == "list":
        for model in models:
            print(
                f"{model.sort_order:>3}  {model.slug:<24} "
                f"active={str(model.active).lower()}  {model.title}"
            )
    elif args.command == "show":
        model = next((item for item in models if item.slug == args.slug), None)
        if model is None:
            raise SystemExit(f"Unknown model slug: {args.slug}")
        print(_dump_model(model), end="")
    elif args.command == "diff":
        asyncio.run(show_diff(models))
    elif args.command == "seed":
        from seed_db import main as seed_main

        asyncio.run(seed_main())


if __name__ == "__main__":
    main()
