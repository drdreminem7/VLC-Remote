"""Deterministic in-memory VLC client used by automated tests."""

from datetime import UTC, datetime
from pathlib import Path

from backend.app.errors import VlcError
from backend.app.models.playback import (
    AudioStatus,
    MediaInformation,
    PlaybackCapabilities,
    PlaybackState,
    PlaybackTime,
    VlcStatus,
)
from backend.app.services.vlc_client import VlcAvailability


def sample_status() -> VlcStatus:
    """Return representative media state without contacting VLC."""

    return VlcStatus(
        state=PlaybackState.PAUSED,
        media=MediaInformation(
            title="Moonrise, Chapter Four",
            filename="moonrise-chapter-four.mkv",
        ),
        time=PlaybackTime(
            elapsed_seconds=1482,
            duration_seconds=6420,
            position=1482 / 6420,
        ),
        audio=AudioStatus(volume_percent=68, muted=False),
        playback_rate=1.0,
        capabilities=PlaybackCapabilities(
            seek=True,
            volume=True,
            rate=True,
        ),
        updated_at=datetime.now(UTC),
    )


class FakeVlcClient:
    """Mutable fake that records only the adapter's fixed typed operations."""

    def __init__(
        self,
        *,
        status: VlcStatus | None = None,
        failure: VlcError | None = None,
    ) -> None:
        self.status = status or sample_status()
        self.failure = failure
        self.commands: list[tuple[str, object | None]] = []
        self.status_calls = 0
        self._last_nonzero_volume = max(1, self.status.audio.volume_percent)

    def _raise_failure(self) -> None:
        if self.failure is not None:
            raise self.failure

    def _updated(self, **changes: object) -> VlcStatus:
        self.status = self.status.model_copy(
            update={**changes, "updated_at": datetime.now(UTC)}
        )
        return self.status

    async def probe(self) -> VlcAvailability:
        if self.failure is not None:
            return VlcAvailability(reachable=False, checked=True)
        return VlcAvailability(reachable=True, checked=True)

    async def get_status(self) -> VlcStatus:
        self._raise_failure()
        self.status_calls += 1
        return self.status

    async def toggle_playback(self) -> VlcStatus:
        self._raise_failure()
        self.commands.append(("toggle_playback", None))
        target = (
            PlaybackState.PAUSED
            if self.status.state is PlaybackState.PLAYING
            else PlaybackState.PLAYING
        )
        return self._updated(state=target)

    async def play(self) -> VlcStatus:
        self._raise_failure()
        self.commands.append(("play", None))
        return self._updated(state=PlaybackState.PLAYING)

    async def pause(self) -> VlcStatus:
        self._raise_failure()
        self.commands.append(("pause", None))
        return self._updated(state=PlaybackState.PAUSED)

    async def stop(self) -> VlcStatus:
        self._raise_failure()
        self.commands.append(("stop", None))
        return self._updated(state=PlaybackState.STOPPED)

    async def play_media(self, file_path: Path) -> VlcStatus:
        self._raise_failure()
        self.commands.append(("play_media", file_path.name))
        return self._updated(
            state=PlaybackState.PLAYING,
            media=MediaInformation(
                title=file_path.stem,
                filename=file_path.name,
            ),
        )

    async def seek_relative(self, seconds: int) -> VlcStatus:
        self._raise_failure()
        self.commands.append(("seek_relative", seconds))
        duration = self.status.time.duration_seconds
        elapsed = max(0, self.status.time.elapsed_seconds + seconds)
        if duration is not None:
            elapsed = min(duration, elapsed)
        position = elapsed / duration if duration else None
        return self._updated(
            time=PlaybackTime(
                elapsed_seconds=elapsed,
                duration_seconds=duration,
                position=position,
            )
        )

    async def seek_absolute(self, seconds: int) -> VlcStatus:
        self._raise_failure()
        self.commands.append(("seek_absolute", seconds))
        duration = self.status.time.duration_seconds
        elapsed = min(seconds, duration) if duration is not None else seconds
        position = elapsed / duration if duration else None
        return self._updated(
            time=PlaybackTime(
                elapsed_seconds=elapsed,
                duration_seconds=duration,
                position=position,
            )
        )

    async def set_volume(self, percent: int) -> VlcStatus:
        self._raise_failure()
        self.commands.append(("set_volume", percent))
        if percent > 0:
            self._last_nonzero_volume = percent
        return self._updated(
            audio=AudioStatus(volume_percent=percent, muted=percent == 0)
        )

    async def set_muted(self, muted: bool) -> VlcStatus:
        self._raise_failure()
        self.commands.append(("set_muted", muted))
        if muted and self.status.audio.volume_percent > 0:
            self._last_nonzero_volume = self.status.audio.volume_percent
        volume = 0 if muted else self._last_nonzero_volume
        return self._updated(audio=AudioStatus(volume_percent=volume, muted=muted))

    async def set_rate(self, rate: float) -> VlcStatus:
        self._raise_failure()
        self.commands.append(("set_rate", rate))
        return self._updated(playback_rate=rate)

    async def select_audio_track(self, track_id: str) -> VlcStatus:
        self._raise_failure()
        self.commands.append(("select_audio_track", track_id))
        return self._updated()

    async def select_subtitle_track(self, track_id: str) -> VlcStatus:
        self._raise_failure()
        self.commands.append(("select_subtitle_track", track_id))
        return self._updated()

    async def next_item(self) -> VlcStatus:
        self._raise_failure()
        self.commands.append(("next_item", None))
        return self._updated()

    async def previous_item(self) -> VlcStatus:
        self._raise_failure()
        self.commands.append(("previous_item", None))
        return self._updated()
