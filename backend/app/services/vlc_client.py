"""Minimal VLC boundary for Phase 1.

No raw VLC command or credential handling belongs in this foundation stub.
Phase 2 will implement this protocol with one reusable HTTPX client.
"""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class VlcAvailability:
    """Result of a safe VLC availability check."""

    reachable: bool
    checked: bool


class VlcClientProtocol(Protocol):
    """The narrow service surface currently needed by the health endpoint."""

    async def probe(self) -> VlcAvailability:
        """Return VLC availability without leaking connection details."""


class UnconfiguredVlcClient:
    """Safe default used until authenticated VLC integration exists."""

    async def probe(self) -> VlcAvailability:
        return VlcAvailability(reachable=False, checked=False)
