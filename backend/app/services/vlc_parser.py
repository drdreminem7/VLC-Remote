"""Parse VLC's unstable raw JSON into the normalized domain model."""

from collections.abc import Mapping
from datetime import UTC, datetime

from backend.app.errors import VlcCommandFailed
from backend.app.models.playback import (
    AudioStatus,
    MediaInformation,
    PlaybackCapabilities,
    PlaybackState,
    PlaybackTime,
    VlcStatus,
)
from backend.app.services.vlc_volume import raw_volume_to_visible_percent

_KNOWN_STATES = {
    "playing": PlaybackState.PLAYING,
    "paused": PlaybackState.PAUSED,
    "stopped": PlaybackState.STOPPED,
    "opening": PlaybackState.OPENING,
    "buffering": PlaybackState.BUFFERING,
}


def _number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return float(value)


def _non_negative_integer(value: object, *, default: int = 0) -> int:
    number = _number(value)
    if number is None:
        return default
    return max(0, int(number))


def _metadata(raw: Mapping[str, object]) -> Mapping[str, object]:
    information = raw.get("information")
    if not isinstance(information, Mapping):
        return {}
    category = information.get("category")
    if not isinstance(category, Mapping):
        return {}
    metadata = category.get("meta")
    if not isinstance(metadata, Mapping):
        return {}
    return metadata


def _text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def parse_vlc_status(raw: Mapping[str, object]) -> VlcStatus:
    """Normalize one `/requests/status.json` response."""

    if not raw:
        raise VlcCommandFailed("VLC returned an empty status response")

    raw_state = raw.get("state")
    state = (
        _KNOWN_STATES.get(raw_state.lower(), PlaybackState.UNKNOWN)
        if isinstance(raw_state, str)
        else PlaybackState.UNKNOWN
    )

    elapsed_seconds = _non_negative_integer(raw.get("time"))
    duration_value = _number(raw.get("length"))
    duration_seconds = (
        max(0, int(duration_value)) if duration_value is not None else None
    )

    position_value = _number(raw.get("position"))
    position = (
        min(1.0, max(0.0, position_value)) if position_value is not None else None
    )
    if position is None and duration_seconds and duration_seconds > 0:
        position = min(1.0, elapsed_seconds / duration_seconds)

    raw_volume = _number(raw.get("volume"))
    volume_percent = (
        raw_volume_to_visible_percent(raw_volume) if raw_volume is not None else 0
    )
    raw_muted = raw.get("mute")
    muted = raw_muted if isinstance(raw_muted, bool) else volume_percent == 0

    raw_rate = _number(raw.get("rate"))
    playback_rate = raw_rate if raw_rate is not None and raw_rate > 0 else 1.0

    metadata = _metadata(raw)
    title = _text(metadata.get("title"))
    filename = _text(metadata.get("filename"))
    if title is None:
        title = filename

    return VlcStatus(
        state=state,
        media=MediaInformation(title=title, filename=filename),
        time=PlaybackTime(
            elapsed_seconds=elapsed_seconds,
            duration_seconds=duration_seconds,
            position=position,
        ),
        audio=AudioStatus(volume_percent=volume_percent, muted=muted),
        playback_rate=playback_rate,
        capabilities=PlaybackCapabilities(
            seek=duration_seconds is not None and duration_seconds > 0,
            volume=raw_volume is not None,
            rate=raw_rate is not None,
        ),
        updated_at=datetime.now(UTC),
    )
