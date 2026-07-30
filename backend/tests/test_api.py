"""Authenticated normalized API tests using the in-memory VLC client."""

from pathlib import Path

from httpx import ASGITransport, AsyncClient

from backend.app.config import Settings
from backend.app.errors import VlcAuthenticationFailed, VlcUnavailable
from backend.app.main import create_app
from backend.app.services.fake_vlc_client import FakeVlcClient
from backend.app.services.movie_library import MovieLibrary
from backend.app.services.playback_resume import (
    PlaybackResumeStore,
    PlaybackResumeTracker,
)

ACCESS_TOKEN = "phase-two-test-token-" + ("a" * 24)


class FakeArtworkLookup:
    async def lookup(self, title: str) -> str | None:
        return "data:image/jpeg;base64,poster" if title == "The Quiet Film" else None

    async def aclose(self) -> None:
        return None


def api_settings() -> Settings:
    return Settings.model_validate(
        {
            "vlc_remote_access_token": ACCESS_TOKEN,
            "vlc_remote_allowed_hosts": "localhost",
        }
    )


def authorization(token: str = ACCESS_TOKEN) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def request_client(
    fake: FakeVlcClient,
    artwork: FakeArtworkLookup | None = None,
    movie_library: MovieLibrary | None = None,
    playback_resume_tracker: PlaybackResumeTracker | None = None,
) -> tuple[AsyncClient, ASGITransport]:
    transport = ASGITransport(
        app=create_app(
            settings=api_settings(),
            vlc_client=fake,
            artwork_lookup=artwork,
            movie_library=movie_library,
            playback_resume_tracker=playback_resume_tracker,
        )
    )
    client = AsyncClient(transport=transport, base_url="http://localhost")
    return client, transport


async def test_status_requires_valid_bearer_token() -> None:
    fake = FakeVlcClient()
    client, _transport = request_client(fake)
    async with client:
        missing = await client.get("/api/v1/status")
        wrong = await client.get(
            "/api/v1/status",
            headers=authorization("x" * len(ACCESS_TOKEN)),
        )
        valid = await client.get("/api/v1/status", headers=authorization())

    assert missing.status_code == 401
    assert wrong.status_code == 401
    assert missing.headers["www-authenticate"] == "Bearer"
    assert missing.json() == {
        "error": {
            "code": "UNAUTHORIZED",
            "message": "This phone is not paired with the Mac remote.",
            "retryable": False,
            "details": None,
        }
    }
    assert valid.status_code == 200
    assert valid.json()["media"]["title"] == "Moonrise, Chapter Four"
    assert valid.json()["capabilities"]["audioTrackSelection"] is False
    assert ACCESS_TOKEN not in valid.text


async def test_artwork_lookup_is_authenticated_and_same_origin() -> None:
    client, _transport = request_client(FakeVlcClient(), FakeArtworkLookup())
    async with client:
        missing = await client.get(
            "/api/v1/artwork",
            params={"title": "The Quiet Film"},
        )
        valid = await client.get(
            "/api/v1/artwork",
            params={"title": "The Quiet Film"},
            headers=authorization(),
        )

    assert missing.status_code == 401
    assert valid.status_code == 200
    assert valid.json() == {"imageData": "data:image/jpeg;base64,poster"}


async def test_library_uses_opaque_ids_and_only_plays_listed_movies(
    tmp_path: Path,
) -> None:
    movie_path = tmp_path / "The.Quiet.Film.2024.mkv"
    movie_path.touch()
    subtitle_path = tmp_path / "The.Quiet.Film.2024.en.srt"
    subtitle_path.touch()
    fake = FakeVlcClient()
    client, _transport = request_client(fake, movie_library=MovieLibrary(tmp_path))

    async with client:
        missing = await client.get("/api/v1/library")
        listing = await client.get("/api/v1/library", headers=authorization())
        movie = listing.json()["movies"][0]
        played = await client.post(
            "/api/v1/library/play",
            headers=authorization(),
            json={"movieId": movie["id"]},
        )
        stale = await client.post(
            "/api/v1/library/play",
            headers=authorization(),
            json={"movieId": "0" * 24},
        )

    assert missing.status_code == 401
    assert listing.status_code == 200
    assert str(tmp_path) not in listing.text
    assert movie["title"] == "The Quiet Film 2024"
    assert played.status_code == 200
    assert played.json()["state"] == "playing"
    assert fake.commands == [
        ("play_media", "The.Quiet.Film.2024.mkv"),
        ("add_subtitle", "The.Quiet.Film.2024.en.srt"),
        ("fullscreen", None),
    ]
    assert played.json()["fullscreen"] is True
    assert stale.status_code == 404
    assert "tmp" not in stale.text


async def test_library_lists_resume_points_and_seeks_only_when_requested(
    tmp_path: Path,
) -> None:
    movie_path = tmp_path / "The.Quiet.Film.2024.mkv"
    movie_path.touch()
    store = PlaybackResumeStore(tmp_path / "state")
    movie_library = MovieLibrary(tmp_path, store)
    movie = (await movie_library.list_movies())[0]
    await store.save(movie.id, 900)
    fake = FakeVlcClient()
    tracker = PlaybackResumeTracker(store)
    client, _transport = request_client(
        fake,
        movie_library=movie_library,
        playback_resume_tracker=tracker,
    )

    async with client:
        listing = await client.get("/api/v1/library", headers=authorization())
        resumed = await client.post(
            "/api/v1/library/play",
            headers=authorization(),
            json={"movieId": movie.id, "resume": True},
        )

    assert listing.json()["movies"][0]["resumeSeconds"] == 900
    assert resumed.status_code == 200
    assert fake.commands == [
        ("play_media", "The.Quiet.Film.2024.mkv"),
        ("fullscreen", None),
        ("seek_absolute", 900),
    ]


async def test_fixed_playback_and_audio_commands_return_updated_status() -> None:
    fake = FakeVlcClient()
    client, _transport = request_client(fake)
    async with client:
        requests = [
            ("POST", "/api/v1/playback/play", None),
            ("POST", "/api/v1/playback/pause", None),
            ("POST", "/api/v1/playback/toggle", None),
            ("POST", "/api/v1/playback/seek", {"mode": "relative", "seconds": -10}),
            ("POST", "/api/v1/playback/seek", {"mode": "absolute", "seconds": 900}),
            ("POST", "/api/v1/audio/volume", {"percent": 200}),
            ("POST", "/api/v1/audio/mute", {"muted": True}),
            ("POST", "/api/v1/playback/rate", {"rate": 1.25}),
            ("POST", "/api/v1/playback/stop", None),
        ]
        responses = [
            await client.request(
                method,
                path,
                headers=authorization(),
                json=body,
            )
            for method, path, body in requests
        ]

    assert all(response.status_code == 200 for response in responses)
    assert fake.commands == [
        ("play", None),
        ("pause", None),
        ("toggle_playback", None),
        ("seek_relative", -10),
        ("seek_absolute", 900),
        ("set_volume", 200),
        ("set_muted", True),
        ("set_rate", 1.25),
        ("stop", None),
    ]
    assert responses[-1].json()["state"] == "stopped"


async def test_invalid_command_values_use_standard_error_shape() -> None:
    fake = FakeVlcClient()
    client, _transport = request_client(fake)
    async with client:
        string_seek = await client.post(
            "/api/v1/playback/seek",
            headers=authorization(),
            json={"mode": "relative", "seconds": "10"},
        )
        huge_seek = await client.post(
            "/api/v1/playback/seek",
            headers=authorization(),
            json={"mode": "relative", "seconds": 3601},
        )
        invalid_volume = await client.post(
            "/api/v1/audio/volume",
            headers=authorization(),
            json={"percent": 201},
        )

    for response in (string_seek, huge_seek, invalid_volume):
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "INVALID_REQUEST"
        assert "input" not in response.text
    assert fake.commands == []


async def test_vlc_unavailability_is_distinct_from_backend_authentication() -> None:
    fake = FakeVlcClient(failure=VlcUnavailable("private connection detail"))
    client, _transport = request_client(fake)
    async with client:
        response = await client.get("/api/v1/status", headers=authorization())

    assert response.status_code == 503
    assert response.json() == {
        "error": {
            "code": "VLC_UNAVAILABLE",
            "message": "The remote service is running, but VLC could not be reached.",
            "retryable": True,
            "details": None,
        }
    }
    assert "private connection detail" not in response.text


async def test_vlc_password_rejection_has_its_own_safe_error() -> None:
    fake = FakeVlcClient(
        failure=VlcAuthenticationFailed("private authentication detail")
    )
    client, _transport = request_client(fake)
    async with client:
        response = await client.get("/api/v1/status", headers=authorization())

    assert response.status_code == 502
    assert response.json()["error"] == {
        "code": "VLC_AUTHENTICATION_FAILED",
        "message": "VLC rejected the password stored by the remote service.",
        "retryable": False,
        "details": None,
    }
    assert "private authentication detail" not in response.text


async def test_unverified_routes_are_not_exposed() -> None:
    fake = FakeVlcClient()
    client, _transport = request_client(fake)
    async with client:
        next_response = await client.post(
            "/api/v1/playback/next",
            headers=authorization(),
        )
        track_response = await client.post(
            "/api/v1/tracks/audio",
            headers=authorization(),
            json={"trackId": "1"},
        )

    assert next_response.status_code == 404
    assert track_response.status_code == 404
