"""GrantScout configuration module."""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration loaded from environment variables."""

    # AWS
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    AWS_PROFILE: str = os.getenv("AWS_PROFILE", "default")

    # Amazon Bedrock
    BEDROCK_MODEL_ID: str = os.getenv(
        "BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-20250514-v1:0"
    )
    BEDROCK_FAST_MODEL_ID: str = os.getenv(
        "BEDROCK_FAST_MODEL_ID", "us.anthropic.claude-haiku-4-5-20250929-v1:0"
    )
    BEDROCK_PREMIUM_MODEL_ID: str = os.getenv(
        "BEDROCK_PREMIUM_MODEL_ID", "us.anthropic.claude-sonnet-4-20250514-v1:0"
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
    SCAN_INTERVAL_HOURS: int = int(os.getenv("SCAN_INTERVAL_HOURS", "6"))

    # Local storage fallback (when AWS is not configured)
    USE_LOCAL_STORAGE: bool = os.getenv("USE_LOCAL_STORAGE", "true").lower() == "true"
    LOCAL_STORAGE_PATH: str = os.getenv("LOCAL_STORAGE_PATH", "./data")

    # Security & Authentication
    AUTH_ENABLED: bool = os.getenv("AUTH_ENABLED", "true").lower() == "true"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "grantscout-sec-key-6f8b9e4a3d2c1b0a9f8e7d6c5b4a3210")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
    MASTER_API_KEY: str = os.getenv("MASTER_API_KEY", "gs_live_8f7e6d5c4b3a210987654321")

    # Amazon Bedrock Guardrails (Optional)
    BEDROCK_GUARDRAIL_ID: str = os.getenv("BEDROCK_GUARDRAIL_ID", "")
    BEDROCK_GUARDRAIL_VERSION: str = os.getenv("BEDROCK_GUARDRAIL_VERSION", "DRAFT")


config = Config()
