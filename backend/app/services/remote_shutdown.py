"""Controlled hand-off from the phone to the Mac launcher for a full shutdown."""

import asyncio
import os
from typing import Protocol

REMOTE_SHUTDOWN_EXIT_CODE = 75
RESPONSE_FLUSH_DELAY_SECONDS = 0.35


class RemoteShutdownProtocol(Protocol):
    """Request a shutdown after the current HTTP response has been sent."""

    async def request(self) -> None: ...


class ProcessRemoteShutdown:
    """End the backend with a code understood by the native Mac launcher."""

    async def request(self) -> None:
        asyncio.create_task(self._exit_after_response())

    async def _exit_after_response(self) -> None:
        await asyncio.sleep(RESPONSE_FLUSH_DELAY_SECONDS)
        os._exit(REMOTE_SHUTDOWN_EXIT_CODE)  # noqa: PLR1722
