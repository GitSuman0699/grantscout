import logging
import os
import secrets

from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class Config:
    """Application configuration loaded from environment variables."""

    # AWS
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    AWS_PROFILE: str = os.getenv("AWS_PROFILE", "default")

    # Amazon Bedrock
    BEDROCK_MODEL_ID: str = os.getenv(
        "BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
    )
    BEDROCK_FAST_MODEL_ID: str = os.getenv(
        "BEDROCK_FAST_MODEL_ID", "us.anthropic.claude-haiku-4-5-20251001-v1:0"
    )
    BEDROCK_PREMIUM_MODEL_ID: str = os.getenv(
        "BEDROCK_PREMIUM_MODEL_ID", os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-5-20250929-v1:0")
    )
    BEDROCK_EMBEDDING_MODEL_ID: str = os.getenv(
        "BEDROCK_EMBEDDING_MODEL_ID", "amazon.titan-embed-text-v2:0"
    )

    # Grants.gov API
    GRANTS_API_BASE_URL: str = os.getenv(
        "GRANTS_API_BASE_URL", "https://api.grants.gov/v1/api"
    )

    # Storage
    S3_BUCKET_NAME: str = os.getenv("S3_BUCKET_NAME", "grantscout-data")
    DYNAMODB_TABLE_NAME: str = os.getenv("DYNAMODB_TABLE_NAME", "grantscout-grants")

    # Server
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))

    # Scan Schedule
    SCAN_INTERVAL_HOURS: int = int(os.getenv("SCAN_INTERVAL_HOURS", "24"))
    AUTO_SCAN_ENABLED: bool = os.getenv("AUTO_SCAN_ENABLED", "false").lower() == "true"

    # Local storage fallback (when AWS is not configured)
    USE_LOCAL_STORAGE: bool = os.getenv("USE_LOCAL_STORAGE", "true").lower() == "true"
    LOCAL_STORAGE_PATH: str = os.getenv("LOCAL_STORAGE_PATH", "./data")

    # Security & Authentication
    AUTH_ENABLED: bool = os.getenv("AUTH_ENABLED", "true").lower() == "true"
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

    # Environment detection
    IS_PRODUCTION: bool = bool(
        os.getenv("RENDER") or os.getenv("ENV") == "production" or os.getenv("ENVIRONMENT") == "production"
    )

    # Secrets strictly sourced from environment; in dev, securely generated if missing
    _env_secret: str = os.getenv("SECRET_KEY", "").strip()
    _env_master_key: str = os.getenv("MASTER_API_KEY", "").strip()

    if IS_PRODUCTION and AUTH_ENABLED:
        if not _env_secret:
            raise RuntimeError("CRITICAL: SECRET_KEY must be configured in production environment.")
        if not _env_master_key:
            raise RuntimeError("CRITICAL: MASTER_API_KEY must be configured in production environment.")

    SECRET_KEY: str = _env_secret or secrets.token_hex(32)
    MASTER_API_KEY: str = _env_master_key or f"gs_dev_{secrets.token_urlsafe(24)}"

    # CORS Whitelist
    CORS_ALLOWED_ORIGINS: list[str] = [
        origin.strip()
        for origin in os.getenv(
            "CORS_ALLOWED_ORIGINS",
            "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000,https://grantscout-api.onrender.com"
        ).split(",")
        if origin.strip()
    ]

    # Amazon Bedrock Guardrails (Optional)
    BEDROCK_GUARDRAIL_ID: str = os.getenv("BEDROCK_GUARDRAIL_ID", "")
    BEDROCK_GUARDRAIL_VERSION: str = os.getenv("BEDROCK_GUARDRAIL_VERSION", "DRAFT")

    # Notification Settings
    SLACK_WEBHOOK_URL: str = os.getenv("SLACK_WEBHOOK_URL", "")


config = Config()
