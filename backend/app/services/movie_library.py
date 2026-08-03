"""Constrained Desktop Movies library discovery and selection."""

import asyncio
import re
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Protocol

from backend.app.models.library import FolderSubtitle, LibraryMovie

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
SUPPORTED_SUBTITLE_SUFFIXES = frozenset(
    {
        ".ass",
        ".dfxp",
        ".idx",
        ".smi",
        ".srt",
        ".ssa",
        ".sub",
        ".sup",
        ".ttml",
        ".vtt",
    }
)
MAX_LIBRARY_MOVIES = 240
MAX_MOVIE_SUBTITLES = 24


class MovieLibraryProtocol(Protocol):
    """The only filesystem boundary used by the movie-picker API."""

    async def list_movies(self) -> tuple[LibraryMovie, ...]: ...

    async def resolve_movie(self, movie_id: str) -> Path | None: ...

    async def subtitles_for(self, movie_path: Path) -> tuple[Path, ...]: ...

    async def folder_subtitles(self, movie_id: str) -> tuple[FolderSubtitle, ...]: ...

    async def resolve_folder_subtitle(
        self, movie_id: str, subtitle_id: str
    ) -> Path | None: ...


@dataclass(frozen=True, slots=True)
class _LibraryEntry:
    movie: LibraryMovie
    path: Path


class MovieLibrary:
    """List supported files below one configured directory, never arbitrary paths."""

    def __init__(self, directory: Path) -> None:
        self._directory = directory.expanduser()

    async def list_movies(self) -> tuple[LibraryMovie, ...]:
        return await asyncio.to_thread(self._movies)

    async def resolve_movie(self, movie_id: str) -> Path | None:
        entries = await asyncio.to_thread(self._entries)
        for entry in entries:
            if entry.movie.id == movie_id:
                return entry.path
        return None

    async def subtitles_for(self, movie_path: Path) -> tuple[Path, ...]:
        """Return only safe external subtitle files beside a selected movie."""

        return await asyncio.to_thread(self._subtitle_paths, movie_path)

    async def folder_subtitles(self, movie_id: str) -> tuple[FolderSubtitle, ...]:
        entry = await asyncio.to_thread(self._entry, movie_id)
        if entry is None:
            return ()
        return await asyncio.to_thread(self._folder_subtitles, entry.path)

    async def resolve_folder_subtitle(
        self, movie_id: str, subtitle_id: str
    ) -> Path | None:
        entry = await asyncio.to_thread(self._entry, movie_id)
        if entry is None:
            return None
        subtitles = await asyncio.to_thread(self._subtitle_paths, entry.path)
        for subtitle_path in subtitles:
            if _subtitle_id(self._relative(subtitle_path)) == subtitle_id:
                return subtitle_path
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

    def _movies(self) -> tuple[LibraryMovie, ...]:
        return tuple(entry.movie for entry in self._entries())

    def _entry(self, movie_id: str) -> _LibraryEntry | None:
        return next(
            (entry for entry in self._entries() if entry.movie.id == movie_id), None
        )

    def _relative(self, path: Path) -> Path:
        return path.resolve(strict=True).relative_to(
            self._directory.resolve(strict=True)
        )

    def _folder_subtitles(self, movie_path: Path) -> tuple[FolderSubtitle, ...]:
        return tuple(
            FolderSubtitle(id=_subtitle_id(self._relative(path)), name=path.name)
            for path in self._subtitle_paths(movie_path)
        )

    def _subtitle_paths(self, movie_path: Path) -> tuple[Path, ...]:
        try:
            root = self._directory.resolve(strict=True)
            resolved_movie = movie_path.resolve(strict=True)
            resolved_movie.relative_to(root)
        except (OSError, ValueError):
            return ()

        subtitles: list[Path] = []
        try:
            for candidate in resolved_movie.parent.iterdir():
                if len(subtitles) >= MAX_MOVIE_SUBTITLES:
                    break
                if candidate.suffix.casefold() not in SUPPORTED_SUBTITLE_SUFFIXES:
                    continue
                try:
                    resolved = candidate.resolve(strict=True)
                    relative = resolved.relative_to(root)
                except (OSError, ValueError):
                    continue
                if (
                    not resolved.is_file()
                    or resolved.parent != resolved_movie.parent
                    or any(part.startswith(".") for part in relative.parts)
                ):
                    continue
                subtitles.append(resolved)
        except OSError:
            return ()

        return tuple(sorted(subtitles, key=lambda path: path.name.casefold()))


def _movie_id(relative_path: Path) -> str:
    """Return an opaque stable identifier without exposing the local path."""

    return sha256(relative_path.as_posix().encode()).hexdigest()[:24]


def _subtitle_id(relative_path: Path) -> str:
    return sha256(f"subtitle:{relative_path.as_posix()}".encode()).hexdigest()[:24]


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
