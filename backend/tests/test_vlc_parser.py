"""Fixture-driven tests for VLC response normalization."""

import json
from pathlib import Path

import pytest

from backend.app.errors import VlcCommandFailed
from backend.app.models.playback import PlaybackState
from backend.app.services.vlc_parser import parse_vlc_status

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> dict[str, object]:
    payload = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_playing_fixture_is_normalized_without_raw_vlc_fields() -> None:
    status = parse_vlc_status(load_fixture("status_playing.json"))

    assert status.state is PlaybackState.PLAYING
    assert status.media.title == "Example Film"
    assert status.media.filename == "example-film.mkv"
    assert status.time.elapsed_seconds == 3724
    assert status.time.duration_seconds == 7210
    assert status.time.position == pytest.approx(0.5165, rel=0.0001)
    assert status.audio.volume_percent == 70
    assert status.audio.muted is False
    assert status.playback_rate == 1.25
    assert status.capabilities.seek is True
    assert status.capabilities.volume is True
    assert status.capabilities.rate is True
    assert status.capabilities.audio_track_selection is False
    assert status.capabilities.subtitle_track_selection is False
    assert status.capabilities.fullscreen is False
    assert status.capabilities.playlist_navigation is False


def test_empty_media_fixture_uses_conservative_defaults() -> None:
    status = parse_vlc_status(load_fixture("status_stopped.json"))

    assert status.state is PlaybackState.STOPPED
    assert status.media.title is None
    assert status.time.duration_seconds == 0
    assert status.capabilities.seek is False
    assert status.audio.muted is True


def test_vlc_maximum_raw_volume_maps_to_200_percent() -> None:
    raw = load_fixture("status_playing.json")
    raw["volume"] = 512

    status = parse_vlc_status(raw)

    assert status.audio.volume_percent == 200


def test_empty_payload_is_rejected() -> None:
    with pytest.raises(VlcCommandFailed):
        parse_vlc_status({})
