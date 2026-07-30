"""Mocked HTTP tests for fixed VLC command mapping and error translation."""

import json
from pathlib import Path

import httpx
import pytest

from backend.app.errors import (
    VlcAuthenticationFailed,
    VlcCommandFailed,
    VlcUnavailable,
)
from backend.app.services.vlc_client import HttpxVlcClient

FIXTURES = Path(__file__).parent / "fixtures"


def fixture_payload() -> dict[str, object]:
    payload = json.loads((FIXTURES / "status_playing.json").read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


async def test_client_uses_basic_auth_and_url_encoded_fixed_parameters() -> None:
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=fixture_payload())

    client = HttpxVlcClient(
        base_url="http://127.0.0.1:8080",
        password="server-only-secret",
        transport=httpx.MockTransport(handler),
    )
    try:
        await client.seek_relative(-10)
        await client.set_volume(70)
        await client.set_volume(200)
        await client.set_rate(1.25)
        await client.play_media(Path("/Users/example/Desktop/Movies/Film One.mkv"))
    finally:
        await client.aclose()

    assert [request.url.path for request in requests] == [
        "/requests/status.json",
        "/requests/status.json",
        "/requests/status.json",
        "/requests/status.json",
        "/requests/status.json",
    ]
    assert dict(requests[0].url.params) == {"command": "seek", "val": "-10S"}
    assert dict(requests[1].url.params) == {"command": "volume", "val": "179"}
    assert dict(requests[2].url.params) == {"command": "volume", "val": "512"}
    assert dict(requests[3].url.params) == {"command": "rate", "val": "1.25"}
    assert dict(requests[4].url.params) == {
        "command": "in_play",
        "input": "file:///Users/example/Desktop/Movies/Film%20One.mkv",
    }
    assert requests[0].headers["Authorization"].startswith("Basic ")
    assert "server-only-secret" not in str(requests[0].url)


async def test_client_distinguishes_authentication_failure() -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(401)

    client = HttpxVlcClient(
        base_url="http://127.0.0.1:8080",
        password="wrong",
        transport=httpx.MockTransport(handler),
    )
    try:
        with pytest.raises(VlcAuthenticationFailed):
            await client.get_status()
    finally:
        await client.aclose()


async def test_client_translates_connection_failure() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    client = HttpxVlcClient(
        base_url="http://127.0.0.1:8080",
        password="secret",
        transport=httpx.MockTransport(handler),
    )
    try:
        with pytest.raises(VlcUnavailable):
            await client.get_status()
    finally:
        await client.aclose()


async def test_client_rejects_malformed_json() -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not json")

    client = HttpxVlcClient(
        base_url="http://127.0.0.1:8080",
        password="secret",
        transport=httpx.MockTransport(handler),
    )
    try:
        with pytest.raises(VlcCommandFailed):
            await client.get_status()
    finally:
        await client.aclose()


async def test_mute_fallback_restores_the_previous_nonzero_volume() -> None:
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=fixture_payload())

    client = HttpxVlcClient(
        base_url="http://127.0.0.1:8080",
        password="secret",
        transport=httpx.MockTransport(handler),
    )
    try:
        await client.set_muted(True)
        await client.set_muted(False)
    finally:
        await client.aclose()

    assert [dict(request.url.params) for request in requests] == [
        {},
        {"command": "volume", "val": "0"},
        {"command": "volume", "val": "179"},
    ]
