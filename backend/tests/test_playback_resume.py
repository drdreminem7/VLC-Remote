from pathlib import Path

from backend.app.services.fake_vlc_client import FakeVlcClient
from backend.app.services.playback_resume import (
    PlaybackResumeStore,
    PlaybackResumeTracker,
)


async def test_tracker_persists_meaningful_progress_and_clears_completed_media(
    tmp_path: Path,
) -> None:
    movie_id = "a" * 24
    store = PlaybackResumeStore(tmp_path)
    tracker = PlaybackResumeTracker(store)
    fake = FakeVlcClient()

    tracker.begin(movie_id)
    await tracker.observe(fake.status)

    assert await store.get(movie_id) == 1482
    assert (tmp_path / "resume-points.json").stat().st_mode & 0o077 == 0

    await fake.seek_absolute(6370)
    await tracker.observe(fake.status)

    assert await store.get(movie_id) is None


async def test_tracker_does_not_create_resume_point_near_the_start(
    tmp_path: Path,
) -> None:
    movie_id = "b" * 24
    store = PlaybackResumeStore(tmp_path)
    tracker = PlaybackResumeTracker(store)
    fake = FakeVlcClient()
    await fake.seek_absolute(30)

    tracker.begin(movie_id)
    await tracker.observe(fake.status)

    assert await store.get(movie_id) is None
