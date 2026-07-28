"""Tests for the public Phase 1 service surface."""

from pathlib import Path

from httpx import ASGITransport, AsyncClient
from pytest import MonkeyPatch

from backend.app.main import create_app


async def test_health_is_public_and_contains_no_secrets() -> None:
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "backend": {"status": "online", "version": "0.1.0"},
        "vlc": {
            "status": "not_configured",
            "reachable": False,
            "checked": False,
        },
    }
    serialized_response = response.text.lower()
    assert "password" not in serialized_response
    assert "token" not in serialized_response
    assert "authorization" not in serialized_response


async def test_root_explains_how_to_build_frontend_when_assets_are_absent(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr("backend.app.main.frontend_directory", lambda: tmp_path)
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")

    assert response.status_code == 200
    assert "Frontend not built" in response.text
