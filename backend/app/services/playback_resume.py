"""Private, Mac-local resume points for movies launched through the library."""

from __future__ import annotations

import asyncio
import json
import os
import stat
from pathlib import Path

from backend.app.models.playback import VlcStatus
from backend.app.services.secret_store import state_directory
from backend.app.services.vlc_client import VlcClientProtocol

RESUME_FILENAME = "resume-points.json"
MINIMUM_RESUME_SECONDS = 60
COMPLETION_MARGIN_SECONDS = 75
WRITE_INTERVAL_SECONDS = 15


class PlaybackResumeStore:
    """Persist opaque movie-id resume positions with private file permissions."""

    def __init__(self, directory: Path | None = None) -> None:
        self._directory = directory or state_directory()
        self._path = self._directory / RESUME_FILENAME
        self._lock = asyncio.Lock()
        self._points: dict[str, int] | None = None

    async def points(self) -> dict[str, int]:
        async with self._lock:
            return dict(await self._load())

    async def get(self, movie_id: str) -> int | None:
        async with self._lock:
            return (await self._load()).get(movie_id)

    async def save(self, movie_id: str, elapsed_seconds: int) -> None:
        async with self._lock:
            points = await self._load()
            points[movie_id] = elapsed_seconds
            await asyncio.to_thread(self._write, points)

    async def clear(self, movie_id: str) -> None:
        async with self._lock:
            points = await self._load()
            if movie_id not in points:
                return
            del points[movie_id]
            await asyncio.to_thread(self._write, points)

    async def _load(self) -> dict[str, int]:
        if self._points is None:
            self._points = await asyncio.to_thread(self._read)
        return self._points

    def _read(self) -> dict[str, int]:
        try:
            file_mode = self._path.lstat().st_mode
            if not stat.S_ISREG(file_mode) or stat.S_ISLNK(file_mode):
                return {}
            if stat.S_IMODE(file_mode) & 0o077:
                self._path.chmod(0o600)
            payload = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return {}
        if not isinstance(payload, dict):
            return {}
        return {
            movie_id: elapsed
            for movie_id, elapsed in payload.items()
            if isinstance(movie_id, str)
            and len(movie_id) == 24
            and isinstance(elapsed, int)
            and elapsed >= MINIMUM_RESUME_SECONDS
        }

    def _write(self, points: dict[str, int]) -> None:
        self._directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        self._directory.chmod(0o700)
        temporary_path = self._path.with_suffix(".tmp")
        descriptor = os.open(
            temporary_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600
        )
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(points, handle, separators=(",", ":"), sort_keys=True)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, self._path)
            self._path.chmod(0o600)
        finally:
            if temporary_path.exists():
                temporary_path.unlink(missing_ok=True)


class PlaybackResumeTracker:
    """Associate polled VLC status with the current library movie."""

    def __init__(self, store: PlaybackResumeStore) -> None:
        self._store = store
        self._active_movie_id: str | None = None
        self._last_saved_seconds: int | None = None

    async def capture_before_replacing_media(self, client: VlcClientProtocol) -> None:
        if self._active_movie_id is None:
            return
        await self.observe(await client.get_status())

    def begin(self, movie_id: str) -> None:
        self._active_movie_id = movie_id
        self._last_saved_seconds = None

    async def resume_point(self, movie_id: str) -> int | None:
        return await self._store.get(movie_id)

    async def clear(self, movie_id: str) -> None:
        await self._store.clear(movie_id)

    async def observe(self, status: VlcStatus) -> None:
        movie_id = self._active_movie_id
        if movie_id is None:
            return
        elapsed = status.time.elapsed_seconds
        duration = status.time.duration_seconds
        if duration is not None and duration - elapsed <= COMPLETION_MARGIN_SECONDS:
            await self.clear(movie_id)
            self._last_saved_seconds = None
            return
        if elapsed < MINIMUM_RESUME_SECONDS:
            return
        if (
            self._last_saved_seconds is not None
            and elapsed - self._last_saved_seconds < WRITE_INTERVAL_SECONDS
        ):
            return
        await self._store.save(movie_id, elapsed)
        self._last_saved_seconds = elapsed
