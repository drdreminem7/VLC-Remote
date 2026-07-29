"""Best-effort movie poster lookup through TMDB with a Wikimedia fallback."""

import base64
from collections.abc import Mapping
from typing import Protocol

import httpx

TMDB_SEARCH_API = "https://api.themoviedb.org/3/search/movie"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w500"
WIKIMEDIA_API = "https://en.wikipedia.org/w/api.php"
MAX_IMAGE_BYTES = 1_500_000


class MovieArtworkLookupProtocol(Protocol):
    async def lookup(self, title: str) -> str | None: ...

    async def aclose(self) -> None: ...


def _normalize_title(value: str) -> str:
    """Normalize punctuation and whitespace for forgiving title matching."""

    return " ".join(
        "".join(
            character if character.isalnum() or character.isspace() else " "
            for character in value.casefold()
        ).split()
    )


def _tmdb_poster_source(payload: object, query: str) -> str | None:
    if not isinstance(payload, Mapping):
        return None
    results = payload.get("results")
    if not isinstance(results, list):
        return None

    normalized_query = _normalize_title(query)
    candidates: list[tuple[int, float, int, str]] = []
    for index, result in enumerate(results):
        if not isinstance(result, Mapping):
            continue
        poster_path = result.get("poster_path")
        title = result.get("title") or result.get("original_title")
        if not isinstance(poster_path, str) or not poster_path.startswith("/"):
            continue
        if not isinstance(title, str):
            title = ""
        normalized_title = _normalize_title(title)
        if normalized_title == normalized_query:
            match_score = 2
        elif (
            normalized_query in normalized_title
            or normalized_title in normalized_query
        ):
            match_score = 1
        else:
            match_score = 0
        popularity_value = result.get("popularity")
        popularity = (
            float(popularity_value)
            if isinstance(popularity_value, (int, float))
            else 0.0
        )
        candidates.append((match_score, popularity, -index, poster_path))

    if not candidates:
        return None
    best = max(candidates)
    return TMDB_IMAGE_BASE + best[3]


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

    def __init__(
        self,
        tmdb_api_token: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._tmdb_api_token = tmdb_api_token.strip() if tmdb_api_token else None
        self._client = httpx.AsyncClient(
            follow_redirects=True,
            headers={"User-Agent": "MacVlcRemote/0.5"},
            timeout=5.0,
            transport=transport,
        )
        self._cache: dict[str, str | None] = {}

    async def _tmdb_source(self, query: str) -> str | None:
        if not self._tmdb_api_token:
            return None
        response = await self._client.get(
            TMDB_SEARCH_API,
            params={
                "query": query,
                "include_adult": "false",
                "language": "en-US",
                "page": "1",
            },
            headers={
                "Authorization": f"Bearer {self._tmdb_api_token}",
                "Accept": "application/json",
            },
        )
        response.raise_for_status()
        return _tmdb_poster_source(response.json(), query)

    async def _wikimedia_source(self, query: str) -> str | None:
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
        response = await self._client.get(WIKIMEDIA_API, params=parameters)
        response.raise_for_status()
        return _thumbnail_source(response.json())

    async def _image_data(self, source: str) -> str | None:
        response = await self._client.get(source)
        response.raise_for_status()
        content_type = response.headers.get("content-type", "").split(";", 1)[0]
        if not content_type.startswith("image/") or len(
            response.content
        ) > MAX_IMAGE_BYTES:
            return None
        return (
            "data:"
            + content_type
            + ";base64,"
            + base64.b64encode(response.content).decode("ascii")
        )

    async def lookup(self, title: str) -> str | None:
        query = title.strip()
        if not query:
            return None
        if query in self._cache:
            return self._cache[query]

        source: str | None = None
        try:
            source = await self._tmdb_source(query)
        except (httpx.HTTPError, ValueError, TypeError):
            source = None
        if source is None:
            try:
                source = await self._wikimedia_source(query)
            except (httpx.HTTPError, ValueError, TypeError):
                source = None
        if source is None:
            self._cache[query] = None
            return None

        try:
            image_data = await self._image_data(source)
        except (httpx.HTTPError, ValueError, TypeError):
            image_data = None
        self._cache[query] = image_data
        return image_data

    async def aclose(self) -> None:
        await self._client.aclose()
