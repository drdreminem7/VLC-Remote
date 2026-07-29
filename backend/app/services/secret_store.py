"""Current-user secret storage for local Mac VLC Remote configuration."""

from __future__ import annotations

import os
import platform
import secrets
import stat
from pathlib import Path

ACCESS_TOKEN_FILENAME = "access-token"
VLC_HTTP_PASSWORD_FILENAME = "vlc-http-password"
TOKEN_MINIMUM_LENGTH = 32


class SecretStoreError(RuntimeError):
    """Raised when a local secret cannot be created or read safely."""


def state_directory(*, home: Path | None = None) -> Path:
    """Return the per-user state directory without creating it."""

    user_home = home or Path.home()
    if platform.system() == "Darwin":
        return user_home / "Library" / "Application Support" / "MacVlcRemote"
    xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config_home:
        return Path(xdg_config_home) / "mac-vlc-remote"
    return user_home / ".config" / "mac-vlc-remote"


def access_token_path(*, directory: Path | None = None) -> Path:
    """Return the access-token file path."""

    return (directory or state_directory()) / ACCESS_TOKEN_FILENAME


def vlc_http_password_path(*, directory: Path | None = None) -> Path:
    """Return the optional VLC HTTP password file path."""

    return (directory or state_directory()) / VLC_HTTP_PASSWORD_FILENAME


def _ensure_private_directory(directory: Path) -> None:
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    directory.chmod(0o700)


def _read_private_file(path: Path) -> str | None:
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError:
        return None

    if not stat.S_ISREG(mode) or stat.S_ISLNK(mode):
        raise SecretStoreError(f"Secret file is not a regular file: {path}")
    if stat.S_IMODE(mode) & 0o077:
        path.chmod(0o600)
    return path.read_text(encoding="utf-8").strip()


def _write_private_file(path: Path, value: str) -> None:
    descriptor: int | None = None
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            descriptor = None
            handle.write(f"{value}\n")
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError:
        return
    finally:
        if descriptor is not None:
            os.close(descriptor)


def is_valid_access_token(value: str) -> bool:
    """Check the format accepted by the browser and bearer dependency."""

    return len(value) >= TOKEN_MINIMUM_LENGTH and all(
        character.isascii() and (character.isalnum() or character in "-_")
        for character in value
    )


def load_or_create_access_token(*, directory: Path | None = None) -> str:
    """Load a strong token or atomically create a new one with mode 0600."""

    active_directory = directory or state_directory()
    _ensure_private_directory(active_directory)
    path = access_token_path(directory=active_directory)

    for _ in range(2):
        token = _read_private_file(path)
        if token is not None:
            if not is_valid_access_token(token):
                raise SecretStoreError(
                    f"Access token file contains an invalid token: {path}"
                )
            return token
        _write_private_file(path, secrets.token_urlsafe(32))

    raise SecretStoreError(f"Could not create access token file: {path}")


def load_vlc_http_password(*, directory: Path | None = None) -> str | None:
    """Read the locally generated VLC HTTP password, if configured."""

    return _read_private_file(vlc_http_password_path(directory=directory))


def load_or_create_vlc_http_password(*, directory: Path | None = None) -> str:
    """Create a strong VLC-only password for the explicit launch helper."""

    active_directory = directory or state_directory()
    _ensure_private_directory(active_directory)
    path = vlc_http_password_path(directory=active_directory)

    for _ in range(2):
        password = _read_private_file(path)
        if password:
            return password
        _write_private_file(path, secrets.token_urlsafe(32))

    raise SecretStoreError(f"Could not create VLC password file: {path}")
