"""
Configuration management for lmn-tools.

Handles loading configuration from environment variables, .env files,
config files, and CLI arguments with proper precedence.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# =============================================================================
# LogicMonitor API Credentials
# =============================================================================


class LMCredentials(BaseModel):
    """
    LogicMonitor API credentials.

    Attributes:
        company: LogicMonitor account/company name
        access_id: API access ID
        access_key: API access key (stored securely)
    """

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    company: Annotated[str, Field(min_length=1, description="LM company/account name")]
    access_id: Annotated[str, Field(min_length=1, description="API access ID")]
    access_key: SecretStr = Field(description="API access key")

    @field_validator("company")
    @classmethod
    def validate_company(cls, v: str) -> str:
        """Company name should be lowercase and stripped."""
        return v.strip().lower()

    @property
    def base_url(self) -> str:
        """Generate the base API URL for this company."""
        return f"https://{self.company}.logicmonitor.com"


# =============================================================================
# NETCONF Credentials
# =============================================================================


class NetconfCredentials(BaseModel):
    """
    NETCONF connection credentials.

    Attributes:
        username: NETCONF username
        password: NETCONF password
        port: NETCONF port (default: 830)
        timeout: Operation timeout in seconds
        hostkey_verify: Whether to verify SSH host keys
    """

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    username: str
    password: SecretStr
    port: Annotated[int, Field(default=830, ge=1, le=65535)]
    timeout: Annotated[int, Field(default=60, ge=1, le=600)]
    hostkey_verify: bool = False


# =============================================================================
# SNMP Credentials
# =============================================================================


class SNMPv2cCredentials(BaseModel):
    """SNMPv2c credentials using community string."""

    model_config = ConfigDict(frozen=True)

    community: SecretStr = Field(default=SecretStr("public"))
    port: Annotated[int, Field(default=161, ge=1, le=65535)]
    timeout: Annotated[int, Field(default=5, ge=1, le=60)]
    retries: Annotated[int, Field(default=2, ge=0, le=10)]


class SNMPv3Credentials(BaseModel):
    """SNMPv3 credentials with authentication and privacy."""

    model_config = ConfigDict(frozen=True)

    username: str
    auth_password: SecretStr
    priv_password: SecretStr
    auth_protocol: Annotated[str, Field(default="SHA", pattern=r"^(MD5|SHA|SHA256)$")]
    priv_protocol: Annotated[
        str, Field(default="AES128", pattern=r"^(DES|3DES|AES128|AES192|AES256)$")
    ]
    port: Annotated[int, Field(default=161, ge=1, le=65535)]
    timeout: Annotated[int, Field(default=5, ge=1, le=60)]
    retries: Annotated[int, Field(default=2, ge=0, le=10)]


# =============================================================================
# Main Settings
# =============================================================================


class LMToolsSettings(BaseSettings):
    """
    Main settings for lmn-tools, loaded from environment and config files.

    Environment variables (prefix LM_):
        LM_COMPANY, LM_ACCESS_ID, LM_ACCESS_KEY
        LM_DEBUG, LM_LOG_LEVEL
        LM_CONFIG_DIR, LM_CACHE_DIR
    """

    model_config = SettingsConfigDict(
        env_prefix="LM_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LogicMonitor API credentials
    company: str = ""
    access_id: str = ""
    access_key: SecretStr = SecretStr("")
    api_timeout: Annotated[int, Field(default=30, ge=1, le=300)]

    # Paths
    config_dir: Path = Field(default_factory=lambda: Path.home() / ".config" / "lmn-tools")
    cache_dir: Path = Field(default_factory=lambda: Path.home() / ".cache" / "lmn-tools")

    # Logging
    debug: bool = False
    log_level: Annotated[str, Field(default="INFO", pattern=r"^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")]

    @property
    def credentials(self) -> LMCredentials | None:
        """Get LM credentials if all required fields are set."""
        if self.company and self.access_id and self.access_key.get_secret_value():
            return LMCredentials(
                company=self.company,
                access_id=self.access_id,
                access_key=self.access_key,
            )
        return None

    @property
    def has_credentials(self) -> bool:
        """Check if credentials are configured."""
        return self.credentials is not None

    def ensure_dirs(self) -> None:
        """Create config and cache directories if they don't exist."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_config_file(self, filename: str) -> Path:
        """Get path to a config file."""
        return self.config_dir / filename

    def get_cache_file(self, filename: str) -> Path:
        """Get path to a cache file."""
        return self.cache_dir / filename


# =============================================================================
# Singleton Settings Access
# =============================================================================

_settings: LMToolsSettings | None = None


def get_settings() -> LMToolsSettings:
    """
    Get the global settings instance.

    Creates a new instance on first call, returns cached instance thereafter.
    """
    global _settings
    if _settings is None:
        _settings = LMToolsSettings()
    return _settings


def reset_settings() -> None:
    """Reset the global settings instance (useful for testing)."""
    global _settings
    _settings = None


# =============================================================================
# LM Client Configuration
# =============================================================================


class LMClientConfig(BaseModel):
    """
    Full LogicMonitor client configuration.

    Attributes:
        credentials: API credentials
        timeout: Request timeout in seconds
        max_retries: Maximum retry attempts for failed requests
        page_size: Default page size for paginated requests
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    credentials: LMCredentials
    timeout: Annotated[int, Field(default=30, ge=1, le=300)]
    max_retries: Annotated[int, Field(default=3, ge=0, le=10)]
    page_size: Annotated[int, Field(default=250, ge=1, le=1000)]


# =============================================================================
# NETCONF Client Configuration
# =============================================================================


class NetconfClientConfig(BaseModel):
    """
    NETCONF client configuration.

    Attributes:
        credentials: Connection credentials
        device_type: Device type hint for connection parameters
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    credentials: NetconfCredentials
    device_type: str | None = None
