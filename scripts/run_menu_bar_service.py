#!/usr/bin/env python3
"""Start the on-demand menu-bar remote without emitting a pairing URL."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from base64 import b64encode
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from backend.app.services.secret_store import load_vlc_http_password

PROJECT_ROOT = Path(__file__).resolve().parents[1]
NODE_BIN_DIRECTORIES = (Path("/usr/local/bin"), Path("/opt/homebrew/bin"))


def fail(message: str) -> int:
    print(message, file=sys.stderr)
    return 1


def run_checked(command: list[str], *, description: str) -> int:
    completed = subprocess.run(command, cwd=PROJECT_ROOT, check=False)
    if completed.returncode != 0:
        return fail(f"{description} failed. See the menu-bar launcher log for details.")
    return 0


def local_vlc_http_is_reusable() -> bool:
    """Accept only the password-protected loopback service created by this app."""
    password = load_vlc_http_password()
    if password is None:
        return False
    credentials = b64encode(f":{password}".encode()).decode("ascii")
    request = Request(
        "http://127.0.0.1:8080/requests/status.json",
        headers={"Authorization": f"Basic {credentials}"},
    )
    try:
        with urlopen(request, timeout=1) as response:  # noqa: S310
            return int(response.status) == 200
    except (HTTPError, URLError, TimeoutError, OSError):
        return False


def configure_node_path() -> str | None:
    """Make Finder/Dock launches see common macOS Node.js installation paths."""
    existing_paths = os.environ.get("PATH", "").split(":")
    search_paths = [str(directory) for directory in NODE_BIN_DIRECTORIES]
    os.environ["PATH"] = ":".join(search_paths + existing_paths)
    return shutil.which("npm")


def main() -> int:
    python = PROJECT_ROOT / ".venv" / "bin" / "python"
    launcher = PROJECT_ROOT / "scripts" / "launch_vlc_http.py"
    if not python.is_file():
        return fail("Dependencies are missing. Run 'make bootstrap' first.")
    if not (PROJECT_ROOT / "node_modules").is_dir():
        return fail("Frontend dependencies are missing. Run 'make bootstrap' first.")
    npm = configure_node_path()
    if npm is None:
        return fail("npm was not found. Run 'make bootstrap' after installing Node.js.")

    if local_vlc_http_is_reusable():
        print("Reusing the existing local VLC HTTP service.")
    elif run_checked([str(python), str(launcher)], description="VLC launch") != 0:
        return 1
    if run_checked([npm, "run", "build"], description="Frontend build") != 0:
        return 1

    allowed_hosts = subprocess.run(
        [str(python), "scripts/show_pairing_qr.py", "--print-allowed-hosts"],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if allowed_hosts.returncode != 0 or not allowed_hosts.stdout.strip():
        return fail("Could not determine trusted local addresses for the remote.")

    environment = os.environ.copy()
    environment["VLC_REMOTE_ALLOWED_HOSTS"] = allowed_hosts.stdout.strip()
    os.execve(
        str(python),
        [
            str(python),
            "-m",
            "uvicorn",
            "backend.app.main:app",
            "--host",
            "0.0.0.0",
            "--port",
            "8000",
        ],
        environment,
    )


if __name__ == "__main__":
    sys.exit(main())
