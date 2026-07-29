"""Best-effort movie poster lookup through Wikimedia's public API."""

import base64
from collections.abc import Mapping
from typing import Protocol

import httpx

WIKIMEDIA_API = "https://en.wikipedia.org/w/api.php"
MAX_IMAGE_BYTES = 1_500_000


class MovieArtworkLookupProtocol(Protocol):
    async def lookup(self, title: str) -> str | None: ...

    async def aclose(self) -> None: ...


def _thumbnail_source(payload: object) -> str | None:
    if not isinstance(payload, Mapping):
        return None
    query = payload.get("query")
    if not isinstance(query, Mapping):
        return None
    pages = query.get("pages")
    if isinstance(pages, Mapping):
        candidates: list[object] = list(pages.values())
    elif isinstance(pages, list):
        candidates = pages
    else:
        return None

    for candidate in candidates:
        if not isinstance(candidate, Mapping):
            continue
        thumbnail = candidate.get("thumbnail")
        if not isinstance(thumbnail, Mapping):
            continue
        source = thumbnail.get("source")
        if isinstance(source, str) and source.startswith(
            "https://upload.wikimedia.org/"
        ):
            return source
    return None


class MovieArtworkLookup:
    """Fetch and cache small poster data URLs on the Mac host."""

    def __init__(self, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._client = httpx.AsyncClient(
            follow_redirects=True,
            headers={"User-Agent": "MacVlcRemote/0.5"},
            timeout=5.0,
            transport=transport,
        )
        self._cache: dict[str, str | None] = {}

    async def lookup(self, title: str) -> str | None:
        query = title.strip()
        if not query:
            return None
        if query in self._cache:
            return self._cache[query]

        parameters = {
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrnamespace": "0",
            "gsrsearch": query,
            "gsrlimit": "3",
            "pithumbsize": "640",
            "piprop": "thumbnail",
            "prop": "pageimages",
        }
        try:
            search_response = await self._client.get(WIKIMEDIA_API, params=parameters)
            search_response.raise_for_status()
            source = _thumbnail_source(search_response.json())
            if source is None:
                self._cache[query] = None
                return None

            image_response = await self._client.get(source)
            image_response.raise_for_status()
            content_type = image_response.headers.get("content-type", "").split(
                ";", 1
            )[0]
            if not content_type.startswith("image/") or len(
                image_response.content
            ) > MAX_IMAGE_BYTES:
                self._cache[query] = None
                return None

            image_data = "data:" + content_type + ";base64," + base64.b64encode(
                image_response.content
            ).decode("ascii")
            self._cache[query] = image_data
            return image_data
        except (httpx.HTTPError, ValueError, TypeError):
            return None

    async def aclose(self) -> None:
        await self._client.aclose()
