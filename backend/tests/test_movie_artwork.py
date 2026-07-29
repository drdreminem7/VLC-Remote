import httpx

from backend.app.services.movie_artwork import MovieArtworkLookup


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
