#!/usr/bin/env python3
"""Explicitly launch VLC with the verified loopback-only HTTP override."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from backend.app.services.secret_store import (
    SecretStoreError,
    load_or_create_vlc_http_password,
    vlc_http_password_path,
)

VLC_EXECUTABLE = Path("/Applications/VLC.app/Contents/MacOS/VLC")


def vlc_is_already_running() -> bool:
    completed = subprocess.run(
        ["pgrep", "-x", "VLC"],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return completed.returncode == 0


def vlc_launch_command(password: str) -> list[str]:
    """Return the temporary, local-only VLC launch configuration."""

    return [
        str(VLC_EXECUTABLE),
        "--intf=macosx",
        "--extraintf=http",
        "--macosx-nativefullscreenmode",
        "--http-host=127.0.0.1",
        "--http-port=8080",
        f"--http-password={password}",
    ]


def main() -> int:
    if not VLC_EXECUTABLE.is_file():
        print(f"VLC was not found at {VLC_EXECUTABLE}.", file=sys.stderr)
        return 1
    if vlc_is_already_running():
        print(
            "VLC is already running. Quit it first, then run 'make vlc-http'. "
            "This helper never changes saved VLC preferences.",
            file=sys.stderr,
        )
        return 1

    try:
        password = load_or_create_vlc_http_password()
    except SecretStoreError as exc:
        print(f"Could not prepare the local VLC password: {exc}", file=sys.stderr)
        return 1

    subprocess.Popen(
        vlc_launch_command(password),
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    print("VLC is launching with its HTTP interface bound to 127.0.0.1:8080.")
    print(f"Its password is stored privately at {vlc_http_password_path()}.")
    print("No VLC preference was changed. Start the remote with 'make run'.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
