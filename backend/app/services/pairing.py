"""Pairing-address construction and local-network discovery."""

from __future__ import annotations

import ipaddress
import re
import socket
import subprocess
from collections.abc import Iterable

_HOST_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.-]{0,252}$")


def pairing_url(*, host: str, port: int, token: str) -> str:
    """Build a fragment-token pairing URL without a server-side query string."""

    if not 1 <= port <= 65535:
        raise ValueError("Pairing port must be between 1 and 65535.")
    candidate = host.strip().strip("[]")
    if not candidate or "/" in candidate or "?" in candidate or "#" in candidate:
        raise ValueError("Pairing host is invalid.")
    try:
        ipaddress.ip_address(candidate)
    except ValueError:
        if not _is_valid_hostname(candidate):
            raise ValueError("Pairing host is invalid.") from None
        rendered_host = candidate
    else:
        rendered_host = f"[{candidate}]" if ":" in candidate else candidate
    return f"http://{rendered_host}:{port}/#token={token}"


def _command_output(command: list[str]) -> str | None:
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=1,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    output = completed.stdout.strip()
    return output if completed.returncode == 0 and output else None


def _is_valid_hostname(value: str) -> bool:
    return bool(_HOST_PATTERN.fullmatch(value)) and not value.startswith(".")


def _private_ipv4_candidates(values: Iterable[str]) -> list[str]:
    addresses: list[str] = []
    for value in values:
        try:
            address = ipaddress.ip_address(value.strip())
        except ValueError:
            continue
        if (
            isinstance(address, ipaddress.IPv4Address)
            and address.is_private
            and not address.is_loopback
            and not address.is_link_local
            and not address.is_unspecified
        ):
            rendered = str(address)
            if rendered not in addresses:
                addresses.append(rendered)
    return addresses


def discover_pairing_hosts() -> list[str]:
    """Discover useful mDNS and private IPv4 pairing addresses on the Mac."""

    hosts: list[str] = []
    local_name = _command_output(["scutil", "--get", "LocalHostName"])
    if local_name and _is_valid_hostname(local_name):
        hosts.append(f"{local_name}.local")

    system_name = socket.gethostname().split(".", maxsplit=1)[0]
    if _is_valid_hostname(system_name):
        system_host = f"{system_name}.local"
        if system_host not in hosts:
            hosts.append(system_host)

    candidates: list[str] = []
    try:
        candidates.extend(
            str(address[4][0])
            for address in socket.getaddrinfo(
                socket.gethostname(), None, socket.AF_INET
            )
        )
    except socket.gaierror:
        pass
    for interface in ("en0", "en1"):
        address = _command_output(["ipconfig", "getifaddr", interface])
        if address:
            candidates.append(address)
    hosts.extend(
        address
        for address in _private_ipv4_candidates(candidates)
        if address not in hosts
    )
    return hosts or ["localhost"]


def trusted_hosts_for_pairing() -> list[str]:
    """Return the host header values needed for local pairing URLs."""

    hosts = ["localhost", "127.0.0.1"]
    hosts.extend(host for host in discover_pairing_hosts() if host not in hosts)
    return hosts
