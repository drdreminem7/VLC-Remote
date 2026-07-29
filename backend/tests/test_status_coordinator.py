"""Concurrency tests for VLC status request deduplication."""

import asyncio

from backend.app.services.fake_vlc_client import FakeVlcClient
from backend.app.services.status_coordinator import StatusCoordinator


class SlowFakeVlcClient(FakeVlcClient):
    async def get_status(self):  # type: ignore[no-untyped-def]
        await asyncio.sleep(0.01)
        return await super().get_status()


async def test_simultaneous_status_reads_share_one_vlc_request() -> None:
    fake = SlowFakeVlcClient()
    coordinator = StatusCoordinator(ttl_seconds=0.3)

    first, second = await asyncio.gather(
        coordinator.get_status(fake),
        coordinator.get_status(fake),
    )

    assert first == second
    assert fake.status_calls == 1
