"""Typed VLC client boundary and production HTTPX implementation."""

import asyncio
from collections.abc import Mapping
from pathlib import Path
from typing import Protocol, cast

import httpx

from backend.app.config import Settings
from backend.app.errors import (
    VlcAuthenticationFailed,
    VlcCommandFailed,
    VlcUnavailable,
)
from backend.app.models.playback import Track, VlcStatus
from backend.app.services.vlc_parser import parse_vlc_status
from backend.app.services.vlc_volume import visible_percent_to_raw_volume

PLAYBACK_READY_ATTEMPTS = 10
PLAYBACK_READY_DELAY_SECONDS = 0.1
FULLSCREEN_READY_DELAY_SECONDS = 0.35
FULLSCREEN_CONFIRMATION_ATTEMPTS = 5
FULLSCREEN_CONFIRMATION_DELAY_SECONDS = 0.1
POSITION_RESTORE_TOLERANCE_SECONDS = 3


class VlcClientProtocol(Protocol):
    """Fixed operations exposed by the backend's VLC boundary."""

    async def probe(self) -> "VlcAvailability": ...

    async def get_status(self) -> VlcStatus: ...

    async def toggle_playback(self) -> VlcStatus: ...

    async def play(self) -> VlcStatus: ...

    async def pause(self) -> VlcStatus: ...

    async def stop(self) -> VlcStatus: ...

    async def play_media(
        self, file_path: Path, subtitle_paths: tuple[Path, ...] = ()
    ) -> VlcStatus: ...

    async def add_subtitle(
        self, subtitle_path: Path, media_path: Path | None = None
    ) -> VlcStatus: ...

    async def seek_relative(self, seconds: int) -> VlcStatus: ...

    async def seek_absolute(self, seconds: int) -> VlcStatus: ...

    async def set_volume(self, percent: int) -> VlcStatus: ...

    async def set_muted(self, muted: bool) -> VlcStatus: ...

    async def set_rate(self, rate: float) -> VlcStatus: ...

    async def select_audio_track(self, track_id: str) -> VlcStatus: ...

    async def select_subtitle_track(self, track_id: str) -> VlcStatus: ...

    async def set_subtitle_delay(self, seconds: float) -> VlcStatus: ...

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

    async def play_media(
        self, file_path: Path, subtitle_paths: tuple[Path, ...] = ()
    ) -> VlcStatus:
        del file_path, subtitle_paths
        return await self._unavailable()

    async def add_subtitle(
        self, subtitle_path: Path, media_path: Path | None = None
    ) -> VlcStatus:
        del subtitle_path, media_path
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

    async def set_subtitle_delay(self, seconds: float) -> VlcStatus:
        del seconds
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
        options: tuple[str, ...] = (),
    ) -> VlcStatus:
        parameters: list[tuple[str, str | int | float | bool | None]] = []
        if command is not None:
            parameters.append(("command", command))
        if value_name is not None and value is not None:
            parameters.append((value_name, value))
        parameters.extend(("option", option) for option in options)

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

    async def play_media(
        self, file_path: Path, subtitle_paths: tuple[Path, ...] = ()
    ) -> VlcStatus:
        """Play a validated movie, load local subtitles, and enter fullscreen."""

        status = await self._request_status(
            command="in_play",
            value_name="input",
            value=file_path.as_uri(),
            options=tuple(
                f":sub-file={subtitle_path}" for subtitle_path in subtitle_paths
            ),
        )
        for _ in range(PLAYBACK_READY_ATTEMPTS):
            if status.state.value not in {"opening", "buffering"}:
                break
            await asyncio.sleep(PLAYBACK_READY_DELAY_SECONDS)
            status = await self.get_status()

        return await self._ensure_fullscreen(status)

    async def _wait_for_new_subtitle_track(
        self, status: VlcStatus, existing_ids: set[str]
    ) -> tuple[VlcStatus, Track | None]:
        """Wait briefly for VLC to publish the stream created by an async command."""

        for _ in range(6):
            new_tracks = [
                track
                for track in status.tracks.subtitles
                if track.id not in existing_ids
            ]
            if new_tracks:
                return status, new_tracks[-1]
            await asyncio.sleep(0.1)
            status = await self.get_status()
        return status, None

    async def _wait_for_ready_playback(self, status: VlcStatus) -> VlcStatus:
        for _ in range(PLAYBACK_READY_ATTEMPTS):
            if status.state.value not in {"opening", "buffering"}:
                break
            await asyncio.sleep(PLAYBACK_READY_DELAY_SECONDS)
            status = await self.get_status()
        return status

    async def _restore_playback_position(
        self, status: VlcStatus, target_seconds: int
    ) -> VlcStatus:
        """Restore playback only after a reloaded VLC input is ready for seeking."""

        await asyncio.sleep(FULLSCREEN_READY_DELAY_SECONDS)
        status = await self.get_status()
        if (
            abs(status.time.elapsed_seconds - target_seconds)
            <= POSITION_RESTORE_TOLERANCE_SECONDS
        ):
            return status
        status = await self.seek_absolute(target_seconds)
        for _ in range(FULLSCREEN_CONFIRMATION_ATTEMPTS):
            if (
                abs(status.time.elapsed_seconds - target_seconds)
                <= POSITION_RESTORE_TOLERANCE_SECONDS
            ):
                return status
            await asyncio.sleep(FULLSCREEN_CONFIRMATION_DELAY_SECONDS)
            status = await self.get_status()
        return status

    async def add_subtitle(
        self, subtitle_path: Path, media_path: Path | None = None
    ) -> VlcStatus:
        """Add and select a subtitle, with VLC input-option fallback if needed."""

        current = await self.get_status()
        existing_ids = {track.id for track in current.tracks.subtitles}
        status = await self._request_status(
            command="addsubtitle",
            value_name="val",
            value=subtitle_path.as_uri(),
        )
        status, added_track = await self._wait_for_new_subtitle_track(
            status, existing_ids
        )
        if added_track is not None:
            return await self.select_subtitle_track(added_track.id)

        if (
            media_path is None
            or current.state.value == "stopped"
            or current.media.filename != media_path.name
        ):
            raise VlcCommandFailed("VLC did not confirm that the subtitle was loaded")

        reload_options = [f":sub-file={subtitle_path}", ":fullscreen"]
        if current.time.elapsed_seconds > 0:
            reload_options.append(f":start-time={current.time.elapsed_seconds}")
        status = await self._request_status(
            command="in_play",
            value_name="input",
            value=media_path.as_uri(),
            # This is an input option, not VLC's toggle-style `fullscreen`
            # command. It keeps the macOS native player full-screen during the
            # reload even when HTTP reports a stale fullscreen flag.
            options=tuple(reload_options),
        )
        status = await self._wait_for_ready_playback(status)
        if current.time.elapsed_seconds > 0:
            status = await self._restore_playback_position(
                status, current.time.elapsed_seconds
            )
        if current.state.value == "paused":
            status = await self.pause()
        status, added_track = await self._wait_for_new_subtitle_track(
            status, existing_ids
        )
        if added_track is None:
            raise VlcCommandFailed("VLC did not confirm that the subtitle was loaded")
        return await self.select_subtitle_track(added_track.id)

    async def _ensure_fullscreen(self, status: VlcStatus) -> VlcStatus:
        """Enter fullscreen after VLC has had time to create its video output."""

        if status.fullscreen:
            return status
        await asyncio.sleep(FULLSCREEN_READY_DELAY_SECONDS)
        status = await self.get_status()
        if status.fullscreen:
            return status

        for attempt in range(2):
            status = await self._request_status(command="fullscreen")
            for _ in range(FULLSCREEN_CONFIRMATION_ATTEMPTS):
                if status.fullscreen:
                    return status
                await asyncio.sleep(FULLSCREEN_CONFIRMATION_DELAY_SECONDS)
                status = await self.get_status()
            if attempt == 0:
                await asyncio.sleep(FULLSCREEN_READY_DELAY_SECONDS)
        return status

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
            value=str(visible_percent_to_raw_volume(percent)),
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

    async def set_subtitle_delay(self, seconds: float) -> VlcStatus:
        return await self._request_status(
            command="subdelay",
            value_name="val",
            value=f"{seconds:.2f}",
        )

    async def next_item(self) -> VlcStatus:
        return await self._request_status(command="pl_next")

    async def previous_item(self) -> VlcStatus:
        return await self._request_status(command="pl_previous")
