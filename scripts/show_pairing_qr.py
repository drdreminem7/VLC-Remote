#!/usr/bin/env python3
"""Display a fragment-token pairing URL and terminal QR code."""

from __future__ import annotations

import argparse
import sys

import qrcode  # type: ignore[import-untyped]

from backend.app.config import Settings
from backend.app.services.pairing import (
    discover_pairing_hosts,
    pairing_url,
    trusted_hosts_for_pairing,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Display a local pairing QR code for VLC Remote."
    )
    parser.add_argument("--host", help="specific hostname or local IP to use")
    parser.add_argument("--port", type=int, default=8000, help="remote service port")
    output_group = parser.add_mutually_exclusive_group()
    output_group.add_argument(
        "--print-allowed-hosts",
        action="store_true",
        help="print a comma-separated trusted-host list without creating a token",
    )
    output_group.add_argument(
        "--print-primary-url",
        action="store_true",
        help="print the first pairing URL for a trusted local launcher",
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_args()
    if arguments.print_allowed_hosts:
        print(",".join(trusted_hosts_for_pairing()))
        return 0

    token = Settings().get_access_token().get_secret_value()
    hosts = [arguments.host] if arguments.host else discover_pairing_hosts()
    urls = [pairing_url(host=host, port=arguments.port, token=token) for host in hosts]

    if arguments.print_primary_url:
        print(urls[0])
        return 0

    print("Scan this QR code on a phone connected to the same home network:")
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, border=1)
    qr.add_data(urls[0])
    qr.make(fit=True)
    qr.print_ascii(invert=True)
    print("\nIf mDNS is unavailable, use one of these local addresses:")
    for url in urls:
        print(url)
    print("The pairing token is in the URL fragment and is not sent to the server.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
