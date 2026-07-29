import httpx
import pytest

from backend.app.services.movie_artwork import MovieArtworkLookup, _tmdb_search_terms


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("The Quiet Film (2024)", ("The Quiet Film", "2024")),
        ("The.Quiet.Film.2024.1080p", ("The Quiet Film", "2024")),
        ("1917", ("1917", None)),
        ("1984 (1984)", ("1984", "1984")),
    ],
)
def test_tmdb_search_terms_handles_parenthesized_and_filename_years(
    title: str, expected: tuple[str, str | None]
) -> None:
    assert _tmdb_search_terms(title) == expected


async def test_lookup_prefers_tmdb_and_sends_bearer_token() -> None:
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.host == "api.themoviedb.org":
            return httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "title": "The Quiet Film",
                            "poster_path": "/quiet-film.jpg",
                            "popularity": 3.0,
                        }
                    ]
                },
            )
        return httpx.Response(
            200,
            content=b"poster",
            headers={"content-type": "image/jpeg"},
        )

    lookup = MovieArtworkLookup(
        tmdb_api_token="tmdb-secret",
        transport=httpx.MockTransport(handler),
    )
    try:
        result = await lookup.lookup("The Quiet Film")
    finally:
        await lookup.aclose()

    assert result == "data:image/jpeg;base64,cG9zdGVy"
    assert len(requests) == 2
    assert requests[0].url.host == "api.themoviedb.org"
    assert requests[0].headers["Authorization"] == "Bearer tmdb-secret"
    assert requests[0].url.params["query"] == "The Quiet Film"
    assert requests[1].url.host == "image.tmdb.org"


async def test_lookup_extracts_a_filename_year_for_tmdb_search() -> None:
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.host == "api.themoviedb.org":
            return httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "title": "The Quiet Film",
                            "poster_path": "/quiet-film.jpg",
                            "popularity": 3.0,
                        }
                    ]
                },
            )
        return httpx.Response(
            200,
            content=b"poster",
            headers={"content-type": "image/jpeg"},
        )

    lookup = MovieArtworkLookup(
        tmdb_api_token="tmdb-secret",
        transport=httpx.MockTransport(handler),
    )
    try:
        result = await lookup.lookup("The Quiet Film (2024).mkv")
    finally:
        await lookup.aclose()

    assert result == "data:image/jpeg;base64,cG9zdGVy"
    assert requests[0].url.params["query"] == "The Quiet Film"
    assert requests[0].url.params["year"] == "2024"


async def test_lookup_retries_a_parenthesized_year_without_a_year_filter() -> None:
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.host == "api.themoviedb.org":
            if request.url.params.get("year") is not None:
                return httpx.Response(200, json={"results": []})
            return httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "title": "The Quiet Film",
                            "poster_path": "/quiet-film.jpg",
                            "popularity": 3.0,
                        }
                    ]
                },
            )
        return httpx.Response(
            200,
            content=b"poster",
            headers={"content-type": "image/jpeg"},
        )

    lookup = MovieArtworkLookup(
        tmdb_api_token="tmdb-secret",
        transport=httpx.MockTransport(handler),
    )
    try:
        result = await lookup.lookup("The Quiet Film (2024).mkv")
    finally:
        await lookup.aclose()

    assert result == "data:image/jpeg;base64,cG9zdGVy"
    assert requests[0].url.params["year"] == "2024"
    assert requests[1].url.params.get("year") is None
    assert requests[2].url.host == "image.tmdb.org"


async def test_lookup_fetches_and_encodes_a_wikimedia_thumbnail() -> None:
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.host == "en.wikipedia.org":
            return httpx.Response(
                200,
                json={
                    "query": {
                        "pages": {
                            "1": {
                                "thumbnail": {
                                    "source": "https://upload.wikimedia.org/poster.jpg"
                                }
                            }
                        }
                    }
                },
            )
        return httpx.Response(
            200,
            content=b"poster",
            headers={"content-type": "image/jpeg"},
        )

    lookup = MovieArtworkLookup(transport=httpx.MockTransport(handler))
    try:
        result = await lookup.lookup("The Quiet Film")
    finally:
        await lookup.aclose()

    assert result == "data:image/jpeg;base64,cG9zdGVy"
    assert len(requests) == 2
    assert requests[0].url.params["gsrsearch"] == "The Quiet Film"


async def test_lookup_returns_none_for_a_search_without_artwork() -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"query": {"pages": {}}})

    lookup = MovieArtworkLookup(transport=httpx.MockTransport(handler))
    try:
        result = await lookup.lookup("Film Without Artwork")
    finally:
        await lookup.aclose()

    assert result is None
