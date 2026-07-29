"""Normalize the installed VLC HTTP interface's volume scale."""

VLC_VISIBLE_VOLUME_MAX = 200
VLC_RAW_VOLUME_MAX = 512


def raw_volume_to_visible_percent(raw_volume: float) -> int:
    """Convert VLC's raw 0–512 value to its visible 0–200% scale."""

    return min(
        VLC_VISIBLE_VOLUME_MAX,
        max(0, round(raw_volume / VLC_RAW_VOLUME_MAX * VLC_VISIBLE_VOLUME_MAX)),
    )


def visible_percent_to_raw_volume(percent: int) -> int:
    """Convert a visible VLC percentage to its raw HTTP command value."""

    return round(percent / VLC_VISIBLE_VOLUME_MAX * VLC_RAW_VOLUME_MAX)
