"""Normalized playback models isolated from VLC's raw JSON representation."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


def to_camel(value: str) -> str:
    """Convert internal snake_case field names to the public camelCase shape."""

    first, *rest = value.split("_")
    return first + "".join(part.capitalize() for part in rest)


class PlaybackModel(BaseModel):
    """Strict, immutable base for normalized playback responses."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        extra="forbid",
        frozen=True,
        populate_by_name=True,
    )


class PlaybackState(StrEnum):
    """States understood by the frontend."""

    PLAYING = "playing"
    PAUSED = "paused"
    STOPPED = "stopped"
    OPENING = "opening"
    BUFFERING = "buffering"
    UNKNOWN = "unknown"


class ConnectionStatus(PlaybackModel):
    backend: str = "online"
    vlc: str = "online"


class MediaInformation(PlaybackModel):
    title: str | None = None
    filename: str | None = None


class PlaybackTime(PlaybackModel):
    elapsed_seconds: int = Field(ge=0)
    duration_seconds: int | None = Field(default=None, ge=0)
    position: float | None = Field(default=None, ge=0.0, le=1.0)


class AudioStatus(PlaybackModel):
    volume_percent: int = Field(ge=0, le=100)
    muted: bool


class Track(PlaybackModel):
    id: str
    name: str
    selected: bool = False


class Tracks(PlaybackModel):
    audio: tuple[Track, ...] = ()
    subtitles: tuple[Track, ...] = ()


class PlaybackCapabilities(PlaybackModel):
    seek: bool
    volume: bool
    rate: bool
    audio_track_selection: bool = False
    subtitle_track_selection: bool = False
    fullscreen: bool = False
    playlist_navigation: bool = False


class VlcStatus(PlaybackModel):
    """Public playback state returned after status and command requests."""

    connection: ConnectionStatus = ConnectionStatus()
    state: PlaybackState
    media: MediaInformation
    time: PlaybackTime
    audio: AudioStatus
    playback_rate: float = Field(gt=0, allow_inf_nan=False)
    tracks: Tracks = Tracks()
    capabilities: PlaybackCapabilities
    updated_at: datetime
