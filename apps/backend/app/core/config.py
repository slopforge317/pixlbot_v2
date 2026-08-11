from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Telegram
    bot_token: str = ""
    telegram_bot_enabled: bool = True
    telegram_test_mode: bool = False  # Use Telegram Test Environment API

    # Database
    database_url: str = "postgresql+asyncpg://pixlbot:pixlbot@localhost:5432/pixlbot"

    # Logging
    log_level: str = "INFO"
    log_dir: str = "logs"
    log_rotation: str = "10 MB"
    log_retention: str = "14 days"
    log_json: bool = False  # JSON format for production
    log_slow_query_ms: int = 100  # Slow query threshold in milliseconds
    log_enqueue: bool = True  # Async logging (doesn't block event loop)

    # KIE API (kie.ai)
    kie_api_key: str = ""
    kie_api_base_url: str = "https://api.kie.ai"
    kie_poll_interval: float = 3.0  # секунды между запросами статуса
    kie_poll_timeout: float = 300.0  # максимальное время ожидания

    # Auth
    init_data_expire_seconds: int = 3600  # 1 hour - защита от replay attacks

    # Webhook settings
    webhook_enabled: bool = False  # False = polling, True = webhook
    webhook_base_url: str = ""  # https://example.com (без trailing slash)
    webhook_path: str = "/webhook/telegram"
    webhook_secret: str = ""  # Secret token для верификации запросов от Telegram

    # KIE Callback (webhook) settings
    kie_callback_enabled: bool = False
    kie_callback_secret: str = ""

    # TMA (Telegram Mini App)
    tma_url: str = ""  # URL Telegram Mini App (e.g. https://tma.pixlbot.online)

    # Bonuses
    welcome_bonus_credits: int = 100  # Credits granted to new users

    # Yandex Cloud Storage (S3-compatible)
    s3_access_key_id: str = ""
    s3_secret_access_key: str = ""
    s3_bucket_name: str = ""
    s3_endpoint_url: str = "https://storage.yandexcloud.net"
    s3_region: str = "ru-central1"
    s3_upload_max_size_bytes: int = 30 * 1024 * 1024  # 30 MB catalog maximum
    s3_presign_upload_expires: int = 600  # 10 min for PUT
    s3_presign_download_expires: int = 3600  # 1 hour for GET

    # YooKassa Payments
    yookassa_shop_id: str = ""
    yookassa_secret_key: str = ""
    yookassa_return_url: str = ""
    yookassa_tax_system_code: int = 2  # 1=ОСН, 2=УСН доходы, 3=УСН доходы-расходы
    yookassa_vat_code: int = 1  # 1=без НДС

    # Stale payment cleanup
    payment_cleanup_enabled: bool = True
    stale_payment_check_interval_seconds: int = 300  # 5 min
    stale_payment_threshold_minutes: int = 15  # Pending older than this → stale

    # Funnel messaging
    funnel_enabled: bool = True
    funnel_check_interval_seconds: int = 30


settings = Settings()
