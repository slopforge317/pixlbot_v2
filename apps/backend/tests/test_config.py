from core.config import Settings


def test_settings_defaults():
    """Test that settings have expected defaults."""
    settings = Settings()
    assert settings.log_level == "INFO"
    assert settings.log_dir == "logs"
    # Database URL should be PostgreSQL (exact value may come from .env)
    assert settings.database_url.startswith("postgresql+asyncpg://")
    assert "pixlbot" in settings.database_url
    assert settings.r2_region == "auto"
    assert settings.r2_endpoint_url == ""
