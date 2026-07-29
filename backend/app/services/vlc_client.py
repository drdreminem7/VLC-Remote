"""Typed VLC client boundary and production HTTPX implementation."""

import asyncio
from collections.abc import Mapping
from typing import Protocol, cast

import httpx

from backend.app.config import Settings
from backend.app.errors import (
    VlcAuthenticationFailed,
    VlcCommandFailed,
    VlcUnavailable,
)
from backend.app.models.playback import VlcStatus
from backend.app.services.vlc_parser import parse_vlc_status


class VlcClientProtocol(Protocol):
    """Fixed operations exposed by the backend's VLC boundary."""

    async def probe(self) -> "VlcAvailability": ...

    async def get_status(self) -> VlcStatus: ...

    async def toggle_playback(self) -> VlcStatus: ...

    async def play(self) -> VlcStatus: ...

    async def pause(self) -> VlcStatus: ...

    async def stop(self) -> VlcStatus: ...

    async def seek_relative(self, seconds: int) -> VlcStatus: ...

    async def seek_absolute(self, seconds: int) -> VlcStatus: ...

    async def set_volume(self, percent: int) -> VlcStatus: ...

    async def set_muted(self, muted: bool) -> VlcStatus: ...

    async def set_rate(self, rate: float) -> VlcStatus: ...

    async def select_audio_track(self, track_id: str) -> VlcStatus: ...

    async def select_subtitle_track(self, track_id: str) -> VlcStatus: ...

    async def next_item(self) -> VlcStatus: ...

    async def previous_item(self) -> VlcStatus: ...


class VlcAvailability:
    """Result of a safe VLC availability check."""

    __slots__ = ("checked", "reachable")

    def __init__(self, *, reachable: bool, checked: bool) -> None:
        self.reachable = reachable
        self.checked = checked


class UnconfiguredVlcClient:
    """Safe default when no server-side VLC password has been configured."""

    async def probe(self) -> VlcAvailability:
        return VlcAvailability(reachable=False, checked=False)

    async def _unavailable(self) -> VlcStatus:
        raise VlcUnavailable("The VLC adapter is not configured")

    async def get_status(self) -> VlcStatus:
        return await self._unavailable()

    async def toggle_playback(self) -> VlcStatus:
        return await self._unavailable()

    async def play(self) -> VlcStatus:
        return await self._unavailable()

    async def pause(self) -> VlcStatus:
        return await self._unavailable()

    async def stop(self) -> VlcStatus:
        return await self._unavailable()

    async def seek_relative(self, seconds: int) -> VlcStatus:
        del seconds
        return await self._unavailable()

    async def seek_absolute(self, seconds: int) -> VlcStatus:
        del seconds
        return await self._unavailable()

    async def set_volume(self, percent: int) -> VlcStatus:
        del percent
        return await self._unavailable()

    async def set_muted(self, muted: bool) -> VlcStatus:
        del muted
        return await self._unavailable()

    async def set_rate(self, rate: float) -> VlcStatus:
        del rate
        return await self._unavailable()

    async def select_audio_track(self, track_id: str) -> VlcStatus:
        del track_id
        return await self._unavailable()

    async def select_subtitle_track(self, track_id: str) -> VlcStatus:
        del track_id
        return await self._unavailable()

    async def next_item(self) -> VlcStatus:
        return await self._unavailable()

    async def previous_item(self) -> VlcStatus:
        return await self._unavailable()


class HttpxVlcClient:
    """VLC HTTP client with fixed endpoints, commands, and short timeouts."""

    def __init__(
        self,
        *,
        base_url: str,
        password: str,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        normalized_base_url = f"{base_url.rstrip('/')}/"
        self._http_client = httpx.AsyncClient(
            auth=httpx.BasicAuth("", password),
            base_url=normalized_base_url,
            follow_redirects=False,
            timeout=httpx.Timeout(
                connect=0.6,
                read=0.9,
                write=0.9,
                pool=0.6,
            ),
            transport=transport,
        )
        self._mute_lock = asyncio.Lock()
        self._last_nonzero_volume = 100

    @classmethod
    def from_settings(cls, settings: Settings) -> "HttpxVlcClient":
        password = settings.get_vlc_http_password()
        if password is None:
            raise ValueError("VLC_HTTP_PASSWORD is required to configure VLC")
        return cls(
            base_url=str(settings.vlc_http_base_url),
            password=password.get_secret_value(),
        )

    async def aclose(self) -> None:
        await self._http_client.aclose()

    async def probe(self) -> VlcAvailability:
        try:
            await self.get_status()
        except (VlcAuthenticationFailed, VlcCommandFailed, VlcUnavailable):
            return VlcAvailability(reachable=False, checked=True)
        return VlcAvailability(reachable=True, checked=True)

    async def _request_status(
        self,
        *,
        command: str | None = None,
        value_name: str | None = None,
        value: str | None = None,
    ) -> VlcStatus:
        parameters: dict[str, str] = {}
        if command is not None:
            parameters["command"] = command
        if value_name is not None and value is not None:
            parameters[value_name] = value

        try:
            response = await self._http_client.get(
                "requests/status.json",
                params=parameters,
            )
        except (
            httpx.ConnectError,
            httpx.ConnectTimeout,
            httpx.PoolTimeout,
            httpx.ReadError,
            httpx.ReadTimeout,
            httpx.RemoteProtocolError,
            httpx.WriteError,
            httpx.WriteTimeout,
        ) as exception:
            raise VlcUnavailable("VLC HTTP connection failed") from exception

        if response.status_code in {401, 403}:
            raise VlcAuthenticationFailed("VLC rejected HTTP Basic authentication")
        if response.is_error:
            raise VlcCommandFailed("VLC returned an unsuccessful HTTP response")

        try:
            payload = response.json()
        except ValueError as exception:
            raise VlcCommandFailed("VLC returned malformed JSON") from exception
        if not isinstance(payload, Mapping):
            raise VlcCommandFailed("VLC returned an unexpected JSON value")

        return parse_vlc_status(cast(Mapping[str, object], payload))

    async def get_status(self) -> VlcStatus:
        return await self._request_status()

    async def toggle_playback(self) -> VlcStatus:
        return await self._request_status(command="pl_pause")

    async def play(self) -> VlcStatus:
        return await self._request_status(command="pl_forceresume")

    async def pause(self) -> VlcStatus:
        return await self._request_status(command="pl_forcepause")

    async def stop(self) -> VlcStatus:
        return await self._request_status(command="pl_stop")

    async def seek_relative(self, seconds: int) -> VlcStatus:
        value = f"{seconds:+d}S"
        return await self._request_status(
            command="seek",
            value_name="val",
            value=value,
        )

    async def seek_absolute(self, seconds: int) -> VlcStatus:
        return await self._request_status(
            command="seek",
            value_name="val",
            value=str(seconds),
        )

    async def set_volume(self, percent: int) -> VlcStatus:
        if percent > 0:
            self._last_nonzero_volume = percent
        return await self._request_status(
            command="volume",
            value_name="val",
            value=f"{percent}%",
        )

    async def set_muted(self, muted: bool) -> VlcStatus:
        async with self._mute_lock:
            if muted:
                current = await self.get_status()
                if current.audio.volume_percent > 0:
                    self._last_nonzero_volume = current.audio.volume_percent
                return await self.set_volume(0)
            return await self.set_volume(self._last_nonzero_volume)

    async def set_rate(self, rate: float) -> VlcStatus:
        return await self._request_status(
            command="rate",
            value_name="val",
            value=str(rate),
        )

    async def select_audio_track(self, track_id: str) -> VlcStatus:
        return await self._request_status(
            command="audio_track",
            value_name="val",
            value=track_id,
        )

    async def select_subtitle_track(self, track_id: str) -> VlcStatus:
        return await self._request_status(
            command="subtitle_track",
            value_name="val",
            value=track_id,
        )

    async def next_item(self) -> VlcStatus:
        return await self._request_status(command="pl_next")

    async def previous_item(self) -> VlcStatus:
        return await self._request_status(command="pl_previous")
