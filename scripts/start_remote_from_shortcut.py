#!/usr/bin/env python3
"""Start VLC Remote from an iPhone Shortcut and print its pairing URL.

This is deliberately a single-purpose entry point. An SSH key used by an
iPhone Shortcut can be restricted to this exact program, preventing it from
opening an interactive shell or running arbitrary commands on the Mac.
"""

from __future__ import annotations

import socket
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REMOTE_PORT = 8000
STARTUP_TIMEOUT_SECONDS = 20


def remote_is_listening() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", REMOTE_PORT), timeout=0.5):
            return True
    except OSError:
        return False


def main() -> int:
    subprocess.run(
        ["/usr/bin/open", "-a", "VLC Remote"],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if remote_is_listening():
            break
        time.sleep(0.5)
    else:
        print("VLC Remote did not start within 20 seconds.", file=sys.stderr)
        return 1

    pairing = subprocess.run(
        [
            str(PROJECT_ROOT / ".venv" / "bin" / "python"),
            str(PROJECT_ROOT / "scripts" / "show_pairing_qr.py"),
            "--print-primary-url",
            "--port",
            str(REMOTE_PORT),
        ],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    url = pairing.stdout.strip()
    if pairing.returncode != 0 or not url.startswith("http://") or "#token=" not in url:
        print(
            "VLC Remote started, but a pairing link could not be created.",
            file=sys.stderr,
        )
        return 1

    print(url)
    return 0


if __name__ == "__main__":
    sys.exit(main())
