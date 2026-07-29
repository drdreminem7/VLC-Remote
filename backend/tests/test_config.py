"""Tests for strict environment-backed settings."""

import pytest
from pydantic import ValidationError

from backend.app.config import Settings


def test_settings_accept_loopback_vlc_and_strong_access_token() -> None:
    settings = Settings.model_validate(
        {
            "vlc_http_base_url": "http://localhost:8080",
            "vlc_http_password": "local-vlc-secret",
            "vlc_remote_access_token": "a" * 43,
            "vlc_remote_allowed_hosts": "localhost, living-room.local",
        }
    )

    assert settings.vlc_is_configured is True
    assert settings.allowed_hosts == ["localhost", "living-room.local"]
    assert settings.vlc_http_password is not None
    assert settings.vlc_http_password.get_secret_value() == "local-vlc-secret"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("vlc_http_base_url", "http://192.168.1.10:8080"),
        ("vlc_http_base_url", "https://127.0.0.1:8080"),
        ("vlc_http_base_url", "http://user:secret@127.0.0.1:8080"),
        ("vlc_http_password", "replace-me"),
        ("vlc_remote_access_token", "too-short"),
        ("vlc_remote_allowed_hosts", "*"),
    ],
)
def test_settings_reject_unsafe_values(field: str, value: str) -> None:
    with pytest.raises(ValidationError):
        Settings.model_validate({field: value})


def test_empty_secrets_leave_services_unconfigured() -> None:
    settings = Settings.model_validate(
        {
            "vlc_http_password": "",
            "vlc_remote_access_token": "",
        }
    )

    assert settings.vlc_is_configured is False
    assert settings.vlc_remote_access_token is None
