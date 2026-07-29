"""Briefly cache and serialize status reads to avoid overwhelming VLC."""

import asyncio
from collections.abc import Callable
from time import monotonic

from backend.app.models.playback import VlcStatus
from backend.app.services.vlc_client import VlcClientProtocol


class StatusCoordinator:
    """Deduplicate concurrent status reads behind a short-lived cache."""

    def __init__(
        self,
        *,
        ttl_seconds: float = 0.3,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        self._ttl_seconds = ttl_seconds
        self._clock = clock
        self._lock = asyncio.Lock()
        self._cached: VlcStatus | None = None
        self._expires_at = 0.0

    async def get_status(self, client: VlcClientProtocol) -> VlcStatus:
        async with self._lock:
            now = self._clock()
            if self._cached is not None and now < self._expires_at:
                return self._cached

            status = await client.get_status()
            self.remember(status)
            return status

    def remember(self, status: VlcStatus) -> None:
        """Make a successful command response immediately available to polling."""

        self._cached = status
        self._expires_at = self._clock() + self._ttl_seconds

    def invalidate(self) -> None:
        self._cached = None
        self._expires_at = 0.0
