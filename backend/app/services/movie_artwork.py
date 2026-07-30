"""Best-effort movie poster lookup through TMDB with a Wikimedia fallback."""

import base64
import re
from collections.abc import Mapping
from typing import Protocol

import httpx

TMDB_SEARCH_API = "https://api.themoviedb.org/3/search/movie"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w500"
WIKIMEDIA_API = "https://en.wikipedia.org/w/api.php"
MAX_IMAGE_BYTES = 1_500_000
YEAR_TOKEN = re.compile(r"(?<!\d)(?:19\d{2}|20\d{2})(?!\d)")
ROMAN_SEQUELS = {
    "ii": "2",
    "iii": "3",
    "iv": "4",
    "v": "5",
    "vi": "6",
    "vii": "7",
    "viii": "8",
    "ix": "9",
    "x": "10",
}
# Some releases use a local sequel number rather than TMDB's primary title.
# Keep these aliases deliberately small and specific; fuzzy matching must not turn
# an unrelated sequel into a popular reboot or prequel.
TMDB_TITLE_ALIASES = {
    "lion king 2": "The Lion King II: Simba's Pride",
    "the lion king 2": "The Lion King II: Simba's Pride",
    "lion king 3": "The Lion King 1½",
    "the lion king 3": "The Lion King 1½",
}


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


def _canonical_title(value: str) -> str:
    """Normalize common Roman sequel markers without losing title words."""

    return " ".join(
        ROMAN_SEQUELS.get(token, token) for token in _normalize_title(value).split()
    )


def _tmdb_title_alias(title: str) -> str:
    """Return a known TMDB primary title for a common local release label."""

    return TMDB_TITLE_ALIASES.get(_normalize_title(title), title)


def _tmdb_search_terms(title: str) -> tuple[str, str | None]:
    """Extract a filename-style release year without damaging numbered titles."""

    sanitized_title = re.sub(r"[._]+", " ", title).strip()
    for match in reversed(tuple(YEAR_TOKEN.finditer(sanitized_title))):
        candidate_title = sanitized_title[: match.start()].strip(" -–—()[]{}")
        if _normalize_title(candidate_title):
            return _tmdb_title_alias(candidate_title), match.group(0)
    return _tmdb_title_alias(sanitized_title), None


def _title_match_score(query: str, candidate: str) -> int:
    """Prefer exact sequel titles over popular entries sharing only a base title."""

    normalized_query = _normalize_title(query)
    normalized_candidate = _normalize_title(candidate)
    canonical_query = _canonical_title(query)
    canonical_candidate = _canonical_title(candidate)
    if (
        normalized_candidate == normalized_query
        or canonical_candidate == canonical_query
    ):
        return 4
    if canonical_candidate.startswith(f"{canonical_query} "):
        return 3
    if canonical_query in canonical_candidate:
        return 2

    query_has_sequel_number = any(token.isdigit() for token in canonical_query.split())
    if not query_has_sequel_number and canonical_candidate in canonical_query:
        return 1
    return 0


def _tmdb_poster_source(payload: object, query: str) -> str | None:
    if not isinstance(payload, Mapping):
        return None
    results = payload.get("results")
    if not isinstance(results, list):
        return None

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
        match_score = _title_match_score(query, title)
        if match_score == 0:
            continue
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
        self._cache: dict[str, str] = {}

    async def _tmdb_source(self, query: str) -> str | None:
        if not self._tmdb_api_token:
            return None
        title, year = _tmdb_search_terms(query)
        parameters = {
            "query": title,
            "include_adult": "false",
            "language": "en-US",
            "page": "1",
        }
        if year is not None:
            parameters["year"] = year
        response = await self._client.get(
            TMDB_SEARCH_API,
            params=parameters,
            headers={
                "Authorization": f"Bearer {self._tmdb_api_token}",
                "Accept": "application/json",
            },
        )
        response.raise_for_status()
        source = _tmdb_poster_source(response.json(), title)
        if source is not None or year is None:
            return source

        parameters.pop("year")
        retry_response = await self._client.get(
            TMDB_SEARCH_API,
            params=parameters,
            headers={
                "Authorization": f"Bearer {self._tmdb_api_token}",
                "Accept": "application/json",
            },
        )
        retry_response.raise_for_status()
        return _tmdb_poster_source(retry_response.json(), title)

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
        if (
            not content_type.startswith("image/")
            or len(response.content) > MAX_IMAGE_BYTES
        ):
            return None
        encoded_image: str = base64.b64encode(response.content).decode("ascii")
        return f"data:{content_type};base64,{encoded_image}"

    async def lookup(self, title: str) -> str | None:
        query = title.strip()
        if not query:
            return None
        cached_artwork = self._cache.get(query)
        if cached_artwork is not None:
            return cached_artwork

        source: str | None = None
        try:
            source = await self._tmdb_source(query)
        except (httpx.HTTPError, ValueError, TypeError):
            source = None
        if source is None:
            try:
                fallback_title, _ = _tmdb_search_terms(query)
                source = await self._wikimedia_source(fallback_title)
            except (httpx.HTTPError, ValueError, TypeError):
                source = None
        if source is None:
            return None

        try:
            image_data = await self._image_data(source)
        except (httpx.HTTPError, ValueError, TypeError):
            image_data = None
        if image_data is not None:
            self._cache[query] = image_data
        return image_data

    async def aclose(self) -> None:
        await self._client.aclose()
