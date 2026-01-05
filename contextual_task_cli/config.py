"""
Configuration management using pydantic-settings.

LEARNING NOTES:
- pydantic-settings automatically loads values from environment variables
- It supports .env files out of the box (via python-dotenv)
- SecretStr hides sensitive values when printing (won't leak API keys in logs)

This module handles:
- API key management (from environment or .env file)
- Model configuration (which Claude model to use)
- Application defaults (max questions, tokens, etc.)

Environment variables are loaded in this priority order:
1. System environment variables (highest priority)
2. .env file in current directory
3. Default values defined in the Settings class
"""

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    LEARNING NOTE:
    BaseSettings is like BaseModel, but it automatically reads from
    environment variables. The field name becomes the env var name
    (with the prefix we configure below).

    Example:
        # In .env or shell:
        TASK_CLI_ANTHROPIC_API_KEY=sk-ant-xxx

        # In Python:
        settings = Settings()
        key = settings.anthropic_api_key.get_secret_value()
    """

    # === API Configuration ===
    anthropic_api_key: SecretStr = Field(
        description="Your Anthropic API key (starts with 'sk-ant-')"
    )

    # === Model Configuration ===
    model_name: str = Field(
        default="claude-sonnet-4-5-20250929",
        description="Claude model to use for conversations"
    )

    max_tokens: int = Field(
        default=4096,
        description="Maximum tokens in Claude's response"
    )

    # === Conversation Configuration ===
    max_questions: int = Field(
        default=5,
        ge=1,  # greater than or equal to 1
        le=10,  # less than or equal to 10
        description="Maximum number of clarifying questions to ask"
    )

    # === Pydantic Settings Configuration ===
    model_config = SettingsConfigDict(
        # Load from .env file if it exists
        env_file=".env",
        env_file_encoding="utf-8",

        # Environment variable names are case-insensitive
        case_sensitive=False,

        # All env vars must start with this prefix
        # e.g., TASK_CLI_ANTHROPIC_API_KEY, TASK_CLI_MODEL_NAME
        env_prefix="TASK_CLI_",

        # Don't fail if extra env vars are present
        extra="ignore",
    )


# ============================================================================
# Singleton Pattern for Settings
# ============================================================================
# We use a module-level variable to cache the Settings instance.
# This avoids re-reading the .env file on every call to get_settings().
# This is a simple form of the "singleton" pattern.

_settings: Settings | None = None


def get_settings() -> Settings:
    """
    Get application settings (lazy-loaded singleton).

    LEARNING NOTE:
    This function uses "lazy loading" - it only creates the Settings
    object when first called, then returns the cached version.

    Why? Two reasons:
    1. Performance: Reading .env file once is faster than every time
    2. Consistency: Same settings object throughout the app lifetime

    Returns:
        Settings: The application settings instance

    Raises:
        ValidationError: If required settings (like API key) are missing
    """
    global _settings

    if _settings is None:
        _settings = Settings()

    return _settings


def reset_settings() -> None:
    """
    Reset the cached settings (useful for testing).

    LEARNING NOTE:
    In tests, you often want to change settings between test cases.
    This function clears the cache so get_settings() creates a fresh instance.
    """
    global _settings
    _settings = None
