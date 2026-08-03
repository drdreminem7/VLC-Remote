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
    Track,
    Tracks,
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


def _category(raw: Mapping[str, object]) -> Mapping[str, object]:
    information = raw.get("information")
    if not isinstance(information, Mapping):
        return {}
    category = information.get("category")
    return category if isinstance(category, Mapping) else {}


def _text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _stream_id(value: object) -> str | None:
    text = _text(value)
    if text is not None:
        return text
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    return None


def _stream_number(key: str) -> str | None:
    """Return the `N` in VLC's `Stream N` status key used by track commands."""

    parts = key.rsplit(" ", 1)
    if len(parts) == 2 and parts[1].isdigit():
        return parts[1]
    return None


def _boolean(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int | float) and not isinstance(value, bool):
        return value != 0
    if isinstance(value, str):
        return value.casefold() in {"1", "true", "yes"}
    return False


def _tracks(raw: Mapping[str, object]) -> Tracks:
    """Extract selectable audio and subtitle streams from VLC's loose status map."""

    selected_audio_id = _stream_id(raw.get("audio-es"))
    selected_id = _stream_id(raw.get("spu-es")) or _stream_id(raw.get("spu"))
    audio: list[Track] = []
    subtitles: list[Track] = []
    for key, value in _category(raw).items():
        if not isinstance(key, str) or not isinstance(value, Mapping):
            continue
        stream_type = _text(value.get("Type")) or _text(value.get("type")) or ""
        normalized_type = stream_type.casefold()
        is_audio = "audio" in normalized_type
        is_subtitle = "subtitle" in normalized_type or "subpicture" in normalized_type
        if not is_audio and not is_subtitle:
            continue
        # VLC's track commands explicitly use the number in `Stream N`, not
        # necessarily the decoder's own `ID` field.
        stream_id = (
            _stream_number(key)
            or _stream_id(value.get("ID"))
            or _stream_id(value.get("id"))
        )
        if stream_id is None:
            continue
        name = (
            _text(value.get("Title"))
            or _text(value.get("title"))
            or _text(value.get("Language"))
            or _text(value.get("language"))
            or f"{'Audio' if is_audio else 'Subtitle'} {stream_id}"
        )
        if is_audio:
            audio.append(
                Track(
                    id=stream_id,
                    name=name,
                    selected=stream_id == selected_audio_id,
                )
            )
        elif is_subtitle:
            subtitles.append(
                Track(id=stream_id, name=name, selected=stream_id == selected_id)
            )
    return Tracks(audio=tuple(audio), subtitles=tuple(subtitles))


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
    raw_subtitle_delay = _number(raw.get("subtitledelay"))
    subtitle_delay_seconds = (
        min(10.0, max(-10.0, raw_subtitle_delay))
        if raw_subtitle_delay is not None
        else 0.0
    )

    metadata = _metadata(raw)
    tracks = _tracks(raw)
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
        subtitle_delay_seconds=subtitle_delay_seconds,
        tracks=tracks,
        capabilities=PlaybackCapabilities(
            seek=duration_seconds is not None and duration_seconds > 0,
            volume=raw_volume is not None,
            rate=raw_rate is not None,
            audio_track_selection=bool(tracks.audio),
            subtitle_track_selection=bool(tracks.subtitles),
        ),
        fullscreen=_boolean(raw.get("fullscreen")),
        updated_at=datetime.now(UTC),
    )
