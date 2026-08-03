"""Authenticated, Mac-only OpenSubtitles search and download client."""

from __future__ import annotations

import asyncio
import os
import re
import secrets
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
from urllib.parse import urlsplit

import httpx

from backend.app.config import Settings
from backend.app.errors import (
    OpenSubtitlesAuthenticationFailed,
    OpenSubtitlesNotConfigured,
    OpenSubtitlesUnavailable,
)
from backend.app.models.library import OnlineSubtitle

API_BASE_URL = "https://api.opensubtitles.com/api/v1"
USER_AGENT = "MacVlcRemote/0.5"
MAX_RESULTS = 18
MAX_SUBTITLE_BYTES = 4_000_000
MOVIE_HASH_CHUNK_BYTES = 64 * 1024
SUPPORTED_SUFFIXES = frozenset({".ass", ".smi", ".srt", ".ssa", ".sub", ".vtt"})
QUALITY_MARKER = re.compile(
    r"(?i)\s+(?:2160p|1080p|720p|480p|bluray|brrip|web[ .-]?dl|webrip|"
    r"dvdrip|hdtv|remux|x26[45]|hevc|av1)\b"
)
YEAR_TOKEN = re.compile(r"(?<!\d)(?:19\d{2}|20\d{2})(?!\d)")
RELEASE_TOKEN = re.compile(
    r"(?i)(?<![a-z0-9])(?:2160p|1080p|720p|480p|bluray|brrip|web[ .-]?dl|"
    r"webrip|dvdrip|hdtv|remux|x26[45]|hevc|av1|hdr10?\+?|"
    r"dolby[ .-]?vision|dv)(?![a-z0-9])"
)


class OpenSubtitlesClientProtocol(Protocol):
    """The online subtitle boundary exposed to authenticated routes only."""

    async def search(
        self, movie_path: Path, language: str
    ) -> tuple[OnlineSubtitle, ...]: ...

    async def download(self, movie_path: Path, subtitle_id: str) -> Path: ...

    async def aclose(self) -> None: ...


@dataclass(frozen=True, slots=True)
class _CachedSubtitle:
    file_id: int | str
    filename: str
    movie_path: Path


def _search_terms(movie_path: Path) -> tuple[str, str | None]:
    """Derive a clean title/year pair from a typical local release filename."""

    value = re.sub(r"[._]+", " ", movie_path.stem).strip()
    marker = QUALITY_MARKER.search(value)
    if marker is not None:
        value = value[: marker.start()].rstrip(" -")
    matches = tuple(YEAR_TOKEN.finditer(value))
    if matches:
        match = matches[-1]
        title = value[: match.start()].strip(" -–—()[]{}")
        if title:
            return title, match.group(0)
    return value or movie_path.stem, None


def _result_value(value: object, *, default: str = "") -> str:
    return value if isinstance(value, str) else default


def _result_number(value: object) -> int:
    return value if isinstance(value, int) and value >= 0 else 0


def _release_tokens(movie_path: Path) -> frozenset[str]:
    """Keep the source/resolution clues normally shared by matching subtitles."""

    return frozenset(
        re.sub(r"[^a-z0-9]+", "", match.group(0).casefold())
        for match in RELEASE_TOKEN.finditer(movie_path.stem)
    )


def _movie_hash(movie_path: Path) -> tuple[str, int] | None:
    """Return OpenSubtitles' 64-bit file hash without loading a movie in memory."""

    try:
        size = movie_path.stat().st_size
        if size < MOVIE_HASH_CHUNK_BYTES * 2:
            return None
        value = size
        with movie_path.open("rb") as handle:
            for offset in (0, size - MOVIE_HASH_CHUNK_BYTES):
                handle.seek(offset)
                chunk = handle.read(MOVIE_HASH_CHUNK_BYTES)
                if len(chunk) != MOVIE_HASH_CHUNK_BYTES:
                    return None
                for index in range(0, MOVIE_HASH_CHUNK_BYTES, 8):
                    value = (
                        value + int.from_bytes(chunk[index : index + 8], "little")
                    ) & 0xFFFFFFFFFFFFFFFF
    except OSError:
        return None
    return f"{value:016x}", size


class UnconfiguredOpenSubtitlesClient:
    """Explicit safe default when the Mac has no online-subtitle credentials."""

    async def search(
        self, movie_path: Path, language: str
    ) -> tuple[OnlineSubtitle, ...]:
        del movie_path, language
        raise OpenSubtitlesNotConfigured

    async def download(self, movie_path: Path, subtitle_id: str) -> Path:
        del movie_path, subtitle_id
        raise OpenSubtitlesNotConfigured

    async def aclose(self) -> None:
        return None


class OpenSubtitlesClient:
    """Small authenticated REST client; credentials and JWT never leave the Mac."""

    def __init__(
        self,
        *,
        username: str,
        password: str,
        api_key: str,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._username = username
        self._password = password
        self._api_key = api_key
        self._client = httpx.AsyncClient(
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
            timeout=20.0,
            transport=transport,
        )
        self._token: str | None = None
        self._base_url = API_BASE_URL
        self._login_lock = asyncio.Lock()
        self._results: dict[str, _CachedSubtitle] = {}

    @classmethod
    def from_settings(cls, settings: Settings) -> OpenSubtitlesClient:
        if not settings.opensubtitles_is_configured:
            raise ValueError("OpenSubtitles credentials are not configured")
        username = settings.opensubtitles_username
        password = settings.opensubtitles_password
        api_key = settings.opensubtitles_api_key
        if username is None or password is None or api_key is None:  # pragma: no cover
            raise ValueError("OpenSubtitles credentials are not configured")
        return cls(
            username=username.get_secret_value(),
            password=password.get_secret_value(),
            api_key=api_key.get_secret_value(),
        )

    def _headers(self, *, authenticated: bool = True) -> dict[str, str]:
        headers = {"Api-Key": self._api_key, "User-Agent": USER_AGENT}
        if authenticated and self._token is not None:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    async def _ensure_login(self) -> None:
        async with self._login_lock:
            if self._token is not None:
                return
            try:
                response = await self._client.post(
                    f"{API_BASE_URL}/login",
                    headers={
                        "Api-Key": self._api_key,
                        "User-Agent": USER_AGENT,
                        "Content-Type": "application/json",
                    },
                    json={"username": self._username, "password": self._password},
                )
            except httpx.HTTPError as exc:
                raise OpenSubtitlesUnavailable from exc
            if response.status_code in {401, 403}:
                raise OpenSubtitlesAuthenticationFailed
            if response.status_code != 200:
                raise OpenSubtitlesUnavailable
            payload = response.json()
            if not isinstance(payload, Mapping):
                raise OpenSubtitlesUnavailable
            token = payload.get("token")
            base_url = payload.get("base_url")
            if not isinstance(token, str) or not token:
                raise OpenSubtitlesAuthenticationFailed
            if isinstance(base_url, str) and base_url:
                parsed = urlsplit(f"https://{base_url.removeprefix('https://')}")
                if parsed.scheme == "https" and parsed.hostname:
                    self._base_url = f"https://{parsed.netloc}/api/v1"
            self._token = token

    async def _api_request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
        json: dict[str, int | str] | None = None,
    ) -> httpx.Response:
        await self._ensure_login()
        try:
            response = await self._client.request(
                method,
                f"{self._base_url}{path}",
                headers=self._headers(),
                params=params,
                json=json,
            )
        except httpx.HTTPError as exc:
            raise OpenSubtitlesUnavailable from exc
        if response.status_code == 401:
            self._token = None
            await self._ensure_login()
            try:
                response = await self._client.request(
                    method,
                    f"{self._base_url}{path}",
                    headers=self._headers(),
                    params=params,
                    json=json,
                )
            except httpx.HTTPError as exc:
                raise OpenSubtitlesUnavailable from exc
        if response.status_code in {401, 403}:
            raise OpenSubtitlesAuthenticationFailed
        if response.status_code == 429 or response.status_code >= 500:
            raise OpenSubtitlesUnavailable
        if not response.is_success:
            raise OpenSubtitlesUnavailable
        return response

    async def search(
        self, movie_path: Path, language: str
    ) -> tuple[OnlineSubtitle, ...]:
        title, year = _search_terms(movie_path)
        parameters: dict[str, str] = {
            "query": f"{title} {year}" if year is not None else title,
            "languages": language,
            "order_by": "download_count",
            "order_direction": "desc",
        }
        if year is not None:
            parameters["year"] = year
        movie_hash = await asyncio.to_thread(_movie_hash, movie_path)
        if movie_hash is not None:
            parameters["moviehash"] = movie_hash[0]
            parameters["moviebytesize"] = str(movie_hash[1])
        response = await self._api_request("GET", "/subtitles", params=parameters)
        payload = response.json()
        if not isinstance(payload, Mapping) or not isinstance(
            payload.get("data"), list
        ):
            raise OpenSubtitlesUnavailable

        results: list[OnlineSubtitle] = []
        resolved_movie = movie_path.resolve()
        release_tokens = _release_tokens(movie_path)
        for item in payload["data"]:
            if not isinstance(item, Mapping):
                continue
            attributes = item.get("attributes")
            if not isinstance(attributes, Mapping):
                continue
            files = attributes.get("files")
            if (
                not isinstance(files, list)
                or not files
                or not isinstance(files[0], Mapping)
            ):
                continue
            file_id = files[0].get("file_id")
            if not isinstance(file_id, (int, str)) or isinstance(file_id, bool):
                continue
            filename = _result_value(files[0].get("file_name"), default="subtitle.srt")
            subtitle_release = _result_value(attributes.get("release"))
            subtitle_tokens = frozenset(
                re.sub(r"[^a-z0-9]+", "", match.group(0).casefold())
                for match in RELEASE_TOKEN.finditer(f"{subtitle_release} {filename}")
            )
            shared_tokens = release_tokens & subtitle_tokens
            release_match = bool(
                release_tokens and len(shared_tokens) >= min(2, len(release_tokens))
            )
            result_id = secrets.token_hex(12)
            self._results[result_id] = _CachedSubtitle(
                file_id=file_id,
                filename=filename,
                movie_path=resolved_movie,
            )
            results.append(
                OnlineSubtitle(
                    id=result_id,
                    filename=filename,
                    language=_result_value(
                        attributes.get("language"), default=language
                    ),
                    release=subtitle_release or None,
                    downloads=_result_number(attributes.get("download_count")),
                    trusted=attributes.get("from_trusted") is True,
                    hearing_impaired=attributes.get("hearing_impaired") is True,
                    moviehash_match=attributes.get("moviehash_match") is True,
                    release_match=release_match,
                )
            )
        return tuple(
            sorted(
                results,
                key=lambda result: (
                    result.moviehash_match,
                    result.release_match,
                    result.trusted,
                    result.downloads,
                ),
                reverse=True,
            )[:MAX_RESULTS]
        )

    async def download(self, movie_path: Path, subtitle_id: str) -> Path:
        result = self._results.get(subtitle_id)
        if result is None or result.movie_path != movie_path.resolve():
            raise OpenSubtitlesUnavailable
        response = await self._api_request(
            "POST", "/download", json={"file_id": result.file_id}
        )
        payload = response.json()
        if not isinstance(payload, Mapping) or not isinstance(payload.get("link"), str):
            raise OpenSubtitlesUnavailable
        link = payload["link"]
        if urlsplit(link).scheme != "https":
            raise OpenSubtitlesUnavailable
        try:
            content = await self._client.get(link)
        except httpx.HTTPError as exc:
            raise OpenSubtitlesUnavailable from exc
        if (
            not content.is_success
            or not content.content
            or len(content.content) > MAX_SUBTITLE_BYTES
            or content.content.lstrip().lower().startswith(b"<html")
        ):
            raise OpenSubtitlesUnavailable
        return await asyncio.to_thread(
            self._save_subtitle, movie_path.resolve(), result.filename, content.content
        )

    @staticmethod
    def _save_subtitle(movie_path: Path, filename: str, content: bytes) -> Path:
        candidate_name = Path(filename).name
        suffix = Path(candidate_name).suffix.casefold()
        if suffix not in SUPPORTED_SUFFIXES:
            suffix = ".srt"
        preferred = movie_path.with_suffix(suffix)
        destination = preferred
        index = 2
        while destination.exists():
            destination = movie_path.with_name(f"{movie_path.stem}.{index}{suffix}")
            index += 1
        descriptor, temporary_name = tempfile.mkstemp(
            dir=movie_path.parent, prefix=".vlc-remote-subtitle-", suffix=".tmp"
        )
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_name, destination)
        except OSError as exc:
            try:
                os.unlink(temporary_name)
            except OSError:
                pass
            raise OpenSubtitlesUnavailable from exc
        return destination

    async def aclose(self) -> None:
        await self._client.aclose()
