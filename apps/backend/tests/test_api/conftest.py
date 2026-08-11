"""API test fixtures."""

import hashlib
import hmac
import json
import os
import time
from collections.abc import AsyncGenerator
from unittest.mock import patch
from urllib.parse import urlencode

import pytest
from api import create_app
from api.deps import get_db_session

# Use app.db paths to match model imports
from db.base import Base
from db.models import AIModel, CreditPackage, PricingVariant, Provider
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Import models to register them with Base.metadata
import app.db.models  # noqa: F401

# Test bot token
TEST_BOT_TOKEN = "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"

# PostgreSQL test database URL
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://pixlbot:pixlbot_test@localhost:5432/pixlbot_pytest",
)


def _calculate_hash(data_check_string: str, bot_token: str) -> str:
    """Calculate HMAC-SHA256 hash for InitData validation."""
    secret_key = hmac.new(
        key=b"WebAppData",
        msg=bot_token.encode(),
        digestmod=hashlib.sha256,
    ).digest()
    return hmac.new(
        key=secret_key,
        msg=data_check_string.encode(),
        digestmod=hashlib.sha256,
    ).hexdigest()


def _build_data_check_string(params: dict[str, str]) -> str:
    """Build sorted data-check-string from params."""
    sorted_params = sorted(params.items(), key=lambda x: x[0])
    return "\n".join(f"{k}={v}" for k, v in sorted_params)


def generate_init_data(
    bot_token: str,
    user_id: int = 123456789,
    first_name: str = "Test",
    last_name: str | None = "User",
    username: str | None = "testuser",
    auth_date: int | None = None,
) -> str:
    """Generate valid initData for testing."""
    if auth_date is None:
        auth_date = int(time.time())

    user_data = {"id": user_id, "first_name": first_name}
    if last_name:
        user_data["last_name"] = last_name
    if username:
        user_data["username"] = username

    params = {
        "auth_date": str(auth_date),
        "user": json.dumps(user_data),
    }

    data_check_string = _build_data_check_string(params)
    hash_value = _calculate_hash(data_check_string, bot_token)
    params["hash"] = hash_value

    return urlencode(params)


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client for testing with PostgreSQL database."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    test_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    test_app = create_app()

    # Override the dependency to use test session maker
    async def override_get_db_session() -> AsyncGenerator[AsyncSession, None]:
        async with test_session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    test_app.dependency_overrides[get_db_session] = override_get_db_session

    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://test",
    ) as ac:
        yield ac

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
def valid_init_data() -> str:
    """Generate valid initData for testing."""
    return generate_init_data(TEST_BOT_TOKEN)


@pytest.fixture
def expired_init_data() -> str:
    """Generate expired initData for testing."""
    old_auth_date = int(time.time()) - 7200  # 2 hours ago
    return generate_init_data(TEST_BOT_TOKEN, auth_date=old_auth_date)


@pytest.fixture
async def auth_client(
    client: AsyncClient, valid_init_data: str
) -> AsyncGenerator[AsyncClient, None]:
    """Return client with pre-configured auth header and mocked bot token."""
    with patch("services.auth.init_data.settings") as mock_settings:
        mock_settings.bot_token = TEST_BOT_TOKEN
        mock_settings.init_data_expire_seconds = 3600
        client.headers["Authorization"] = f"tma {valid_init_data}"
        yield client


@pytest.fixture
async def db_session_and_client() -> (
    AsyncGenerator[tuple[AsyncSession, AsyncClient], None]
):
    """Create both db session and client sharing the same database."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    test_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    test_app = create_app()

    async def override_get_db_session() -> AsyncGenerator[AsyncSession, None]:
        async with test_session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    test_app.dependency_overrides[get_db_session] = override_get_db_session

    async with test_session_maker() as session:
        async with AsyncClient(
            transport=ASGITransport(app=test_app),
            base_url="http://test",
        ) as ac:
            yield session, ac

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def seed_models(
    db_session_and_client: tuple[AsyncSession, AsyncClient],
) -> tuple[list[Provider], AsyncClient]:
    """Seed providers with models and pricing variants, return them with client."""
    session, client = db_session_and_client

    # Create image provider
    image_provider = Provider(
        slug="test-image-provider",
        title="Test Image Provider",
        gen_type="image",
        active=True,
    )
    session.add(image_provider)
    await session.flush()

    # Create image model
    image_model = AIModel(
        provider_id=image_provider.id,
        api_model_id="test/text-to-image",
        title="Text-to-Image",
        input_schema={
            "prompt": {"type": "string", "required": True},
            "aspect_ratio": {"type": "string", "required": False},
        },
        variant_keys=[],
        active=True,
    )
    session.add(image_model)
    await session.flush()

    # Create pricing variants for image model
    pv1 = PricingVariant(
        model_id=image_model.id,
        variant_values={},
        price=10,
        active=True,
    )
    pv2 = PricingVariant(
        model_id=image_model.id,
        variant_values={},
        price=25,
        active=True,
    )
    pv_inactive = PricingVariant(
        model_id=image_model.id,
        variant_values={},
        price=100,
        active=False,
    )
    session.add_all([pv1, pv2, pv_inactive])

    # Create video provider
    video_provider = Provider(
        slug="test-video-provider",
        title="Test Video Provider",
        gen_type="video",
        active=True,
    )
    session.add(video_provider)
    await session.flush()

    # Create video model
    video_model = AIModel(
        provider_id=video_provider.id,
        api_model_id="test/text-to-video",
        title="Text-to-Video",
        input_schema={
            "prompt": {"type": "string", "required": True},
        },
        variant_keys=["duration"],
        active=True,
    )
    session.add(video_model)
    await session.flush()

    video_pv = PricingVariant(
        model_id=video_model.id,
        variant_values={"duration": "5"},
        price=50,
        active=True,
    )
    session.add(video_pv)

    await session.commit()
    return [image_provider, video_provider], client


@pytest.fixture
async def seed_packages(
    db_session_and_client: tuple[AsyncSession, AsyncClient],
) -> tuple[list[CreditPackage], AsyncClient]:
    """Seed credit packages and return them with client."""
    session, client = db_session_and_client

    packages = [
        CreditPackage(
            name="Starter",
            description="Perfect for trying out",
            credit_amount=50,
            fiat_price=9900,  # 99.00 RUB
            is_active=True,
        ),
        CreditPackage(
            name="Standard",
            description="Most popular choice",
            credit_amount=150,
            fiat_price=24900,  # 249.00 RUB
            is_active=True,
        ),
        CreditPackage(
            name="Pro",
            description="Best value",
            credit_amount=500,
            fiat_price=69900,  # 699.00 RUB
            is_active=True,
        ),
        CreditPackage(
            name="Inactive",
            description="Should not appear",
            credit_amount=1000,
            fiat_price=99900,
            is_active=False,
        ),
    ]
    session.add_all(packages)
    await session.commit()

    # Return only active packages (first 3)
    return packages[:3], client
