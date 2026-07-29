"""Tests for local token and VLC-password storage."""

import stat
from pathlib import Path

import pytest

from backend.app.services.secret_store import (
    SecretStoreError,
    access_token_path,
    is_valid_access_token,
    load_or_create_access_token,
    load_or_create_vlc_http_password,
    load_vlc_http_password,
    vlc_http_password_path,
)


def test_access_token_is_created_once_with_private_permissions(tmp_path: Path) -> None:
    token = load_or_create_access_token(directory=tmp_path)
    path = access_token_path(directory=tmp_path)

    assert is_valid_access_token(token)
    assert load_or_create_access_token(directory=tmp_path) == token
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert stat.S_IMODE(tmp_path.stat().st_mode) == 0o700


def test_existing_token_permissions_are_tightened(tmp_path: Path) -> None:
    path = access_token_path(directory=tmp_path)
    path.write_text("a" * 43, encoding="utf-8")
    path.chmod(0o644)

    assert load_or_create_access_token(directory=tmp_path) == "a" * 43
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_invalid_existing_token_is_rejected(tmp_path: Path) -> None:
    access_token_path(directory=tmp_path).write_text("not-valid", encoding="utf-8")

    with pytest.raises(SecretStoreError, match="invalid token"):
        load_or_create_access_token(directory=tmp_path)


def test_vlc_password_is_created_only_by_explicit_helper(tmp_path: Path) -> None:
    assert load_vlc_http_password(directory=tmp_path) is None

    password = load_or_create_vlc_http_password(directory=tmp_path)

    assert load_vlc_http_password(directory=tmp_path) == password
    assert (
        stat.S_IMODE(vlc_http_password_path(directory=tmp_path).stat().st_mode) == 0o600
    )
