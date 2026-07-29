"""Validated application configuration loaded from environment variables."""

from functools import lru_cache
from typing import Literal
from urllib.parse import urlsplit

from pydantic import AnyHttpUrl, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings with secrets kept behind ``SecretStr`` values."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    vlc_remote_host: str = "127.0.0.1"
    vlc_remote_port: int = Field(default=8000, ge=1, le=65535)
    vlc_http_base_url: AnyHttpUrl = AnyHttpUrl("http://127.0.0.1:8080")
    vlc_http_password: SecretStr | None = None
    vlc_remote_access_token: SecretStr | None = None
    vlc_remote_log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    vlc_remote_allowed_hosts: str = "localhost,127.0.0.1"
    vlc_remote_enable_discovery: bool = True

    @field_validator("vlc_http_password", "vlc_remote_access_token", mode="before")
    @classmethod
    def empty_secret_is_unconfigured(cls, value: object) -> object:
        """Treat empty environment values as intentionally unconfigured."""

        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("vlc_http_password")
    @classmethod
    def reject_placeholder_password(cls, value: SecretStr | None) -> SecretStr | None:
        if value is not None and value.get_secret_value() == "replace-me":
            raise ValueError("VLC_HTTP_PASSWORD still contains the example placeholder")
        return value

    @field_validator("vlc_remote_access_token")
    @classmethod
    def validate_access_token(cls, value: SecretStr | None) -> SecretStr | None:
        if value is not None and len(value.get_secret_value()) < 32:
            raise ValueError(
                "VLC_REMOTE_ACCESS_TOKEN must contain at least 32 characters"
            )
        return value

    @field_validator("vlc_http_base_url")
    @classmethod
    def require_loopback_vlc_url(cls, value: AnyHttpUrl) -> AnyHttpUrl:
        parsed = urlsplit(str(value))
        if parsed.scheme != "http":
            raise ValueError("VLC_HTTP_BASE_URL must use plain HTTP on loopback")
        if parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("VLC_HTTP_BASE_URL must target the local Mac only")
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError(
                "VLC_HTTP_BASE_URL cannot contain credentials, a query, or a fragment"
            )
        return value

    @field_validator("vlc_remote_allowed_hosts")
    @classmethod
    def reject_wildcard_allowed_hosts(cls, value: str) -> str:
        hosts = [host.strip() for host in value.split(",") if host.strip()]
        if not hosts:
            raise ValueError("VLC_REMOTE_ALLOWED_HOSTS must contain at least one host")
        if "*" in hosts:
            raise ValueError("Wildcard trusted hosts are not allowed")
        return ",".join(hosts)

    @property
    def allowed_hosts(self) -> list[str]:
        """Return the validated host allow-list."""

        return self.vlc_remote_allowed_hosts.split(",")

    @property
    def vlc_is_configured(self) -> bool:
        """Whether enough secret material exists to construct the VLC client."""

        return self.vlc_http_password is not None


@lru_cache
def get_settings() -> Settings:
    """Load and cache process-wide settings."""

    return Settings()
