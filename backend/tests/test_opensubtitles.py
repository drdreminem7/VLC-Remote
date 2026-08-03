from pathlib import Path

import httpx

from backend.app.services.opensubtitles import (
    OpenSubtitlesClient,
    _movie_hash,
    _search_terms,
)


def test_search_terms_removes_release_markers_and_extracts_year() -> None:
    assert _search_terms(Path("Chinatown.1974.2160p.BluRay.mkv")) == (
        "Chinatown",
        "1974",
    )
    assert _search_terms(Path("Mikey.and.Nicky.(1976).1080p.mkv")) == (
        "Mikey and Nicky",
        "1976",
    )


def test_movie_hash_uses_the_file_contents_without_loading_the_whole_movie(
    tmp_path: Path,
) -> None:
    movie = tmp_path / "Example.2024.2160p.BluRay.mkv"
    movie.write_bytes((b"12345678" * 16384) + (b"abcdefgh" * 16384))

    result = _movie_hash(movie)

    assert result is not None
    assert result[1] == 262144
    assert len(result[0]) == 16


async def test_search_logs_in_and_returns_safe_short_lived_result(
    tmp_path: Path,
) -> None:
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.endswith("/login"):
            return httpx.Response(
                200,
                json={"token": "jwt-token", "base_url": "api.opensubtitles.com"},
            )
        return httpx.Response(
            200,
            json={
                "data": [
                    {
                        "type": "subtitle",
                        "attributes": {
                            "language": "en",
                            "release": "Example release",
                            "download_count": 42,
                            "from_trusted": True,
                            "hearing_impaired": False,
                            "moviehash_match": True,
                            "files": [{"file_id": 1234, "file_name": "Example.en.srt"}],
                        },
                    }
                ]
            },
        )

    movie = tmp_path / "Example.2024.1080p.mkv"
    movie.touch()
    client = OpenSubtitlesClient(
        username="account",
        password="password",
        api_key="api-key",
        transport=httpx.MockTransport(handler),
    )
    try:
        results = await client.search(movie, "en")
    finally:
        await client.aclose()

    assert len(results) == 1
    assert results[0].filename == "Example.en.srt"
    assert results[0].trusted is True
    assert requests[0].url.path == "/api/v1/login"
    assert requests[0].headers["Api-Key"] == "api-key"
    assert requests[1].url.params["query"] == "Example 2024"
    assert requests[1].url.params["year"] == "2024"
    assert requests[1].headers["Authorization"] == "Bearer jwt-token"


async def test_download_saves_next_to_movie_without_overwriting_existing_file(
    tmp_path: Path,
) -> None:
    movie = tmp_path / "Example.2024.mkv"
    movie.touch()
    movie.with_suffix(".srt").write_text("existing", encoding="utf-8")

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/login"):
            return httpx.Response(200, json={"token": "jwt-token"})
        if request.url.path.endswith("/subtitles"):
            return httpx.Response(
                200,
                json={
                    "data": [
                        {
                            "type": "subtitle",
                            "attributes": {
                                "language": "en",
                                "files": [
                                    {"file_id": "1234", "file_name": "Example.en.srt"}
                                ],
                            },
                        }
                    ]
                },
            )
        if request.url.path.endswith("/download"):
            return httpx.Response(200, json={"link": "https://cdn.example/subtitle"})
        return httpx.Response(200, content=b"1\n00:00:00,000 --> 00:00:01,000\nHello\n")

    client = OpenSubtitlesClient(
        username="account",
        password="password",
        api_key="api-key",
        transport=httpx.MockTransport(handler),
    )
    try:
        result = (await client.search(movie, "en"))[0]
        saved_path = await client.download(movie, result.id)
    finally:
        await client.aclose()

    assert saved_path == tmp_path / "Example.2024.2.srt"
    assert saved_path.read_text(encoding="utf-8").endswith("Hello\n")
