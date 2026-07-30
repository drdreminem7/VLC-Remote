"""Constrained Desktop Movies library discovery and selection."""

import asyncio
import re
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Protocol

from backend.app.models.library import LibraryMovie

SUPPORTED_MOVIE_SUFFIXES = frozenset(
    {
        ".3g2",
        ".3gp",
        ".asf",
        ".avi",
        ".divx",
        ".flv",
        ".m2ts",
        ".m4v",
        ".mkv",
        ".mov",
        ".mp4",
        ".mpeg",
        ".mpg",
        ".mts",
        ".ogm",
        ".ogv",
        ".ts",
        ".vob",
        ".webm",
        ".wmv",
    }
)
MAX_LIBRARY_MOVIES = 240


class MovieLibraryProtocol(Protocol):
    """The only filesystem boundary used by the movie-picker API."""

    async def list_movies(self) -> tuple[LibraryMovie, ...]: ...

    async def resolve_movie(self, movie_id: str) -> Path | None: ...


@dataclass(frozen=True, slots=True)
class _LibraryEntry:
    movie: LibraryMovie
    path: Path


class MovieLibrary:
    """List supported files below one configured directory, never arbitrary paths."""

    def __init__(self, directory: Path) -> None:
        self._directory = directory.expanduser()

    async def list_movies(self) -> tuple[LibraryMovie, ...]:
        return tuple(entry.movie for entry in await asyncio.to_thread(self._entries))

    async def resolve_movie(self, movie_id: str) -> Path | None:
        entries = await asyncio.to_thread(self._entries)
        for entry in entries:
            if entry.movie.id == movie_id:
                return entry.path
        return None

    def _entries(self) -> tuple[_LibraryEntry, ...]:
        try:
            root = self._directory.resolve(strict=True)
        except OSError:
            return ()
        if not root.is_dir():
            return ()

        entries: list[_LibraryEntry] = []
        try:
            candidates = root.rglob("*")
            for candidate in candidates:
                if len(entries) >= MAX_LIBRARY_MOVIES:
                    break
                if candidate.suffix.casefold() not in SUPPORTED_MOVIE_SUFFIXES:
                    continue
                try:
                    resolved = candidate.resolve(strict=True)
                    relative = resolved.relative_to(root)
                except (OSError, ValueError):
                    continue
                if not resolved.is_file() or any(
                    part.startswith(".") for part in relative.parts
                ):
                    continue
                artwork_query = resolved.stem
                entries.append(
                    _LibraryEntry(
                        movie=LibraryMovie(
                            id=_movie_id(relative),
                            title=_display_title(artwork_query),
                            artwork_query=artwork_query,
                        ),
                        path=resolved,
                    )
                )
        except OSError:
            return ()

        return tuple(sorted(entries, key=lambda entry: entry.movie.title.casefold()))


def _movie_id(relative_path: Path) -> str:
    """Return an opaque stable identifier without exposing the local path."""

    return sha256(relative_path.as_posix().encode("utf-8")).hexdigest()[:24]


def _display_title(stem: str) -> str:
    """Make common release filenames readable without changing the artwork query."""

    title = re.sub(r"[._]+", " ", stem).strip()
    quality_marker = re.search(
        r"(?i)\s+(?:2160p|1080p|720p|480p|bluray|brrip|web[ .-]?dl|webrip|"
        r"dvdrip|hdtv|remux|x26[45]|hevc|av1)\b",
        title,
    )
    if quality_marker is not None:
        title = title[: quality_marker.start()].rstrip(" -")
    return title or stem
