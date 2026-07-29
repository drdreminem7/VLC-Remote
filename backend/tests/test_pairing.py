"""Tests for safe fragment-based pairing URLs and local discovery helpers."""

import pytest

from backend.app.services.pairing import (
    _canonical_hostname,
    _private_ipv4_candidates,
    pairing_url,
)


def test_pairing_url_keeps_token_out_of_server_side_request() -> None:
    url = pairing_url(host="living-room.local", port=8000, token="a" * 43)

    assert url == f"http://living-room.local:8000/#token={'a' * 43}"


def test_pairing_url_brackets_an_ipv6_host() -> None:
    assert pairing_url(host="::1", port=8000, token="a" * 43).startswith(
        "http://[::1]:8000/#token="
    )


@pytest.mark.parametrize(
    "host", ["", "host/path", "host?query", "host#fragment", "host:8000"]
)
def test_pairing_url_rejects_unsafe_host_values(host: str) -> None:
    with pytest.raises(ValueError, match="invalid"):
        pairing_url(host=host, port=8000, token="a" * 43)


def test_private_ipv4_candidates_exclude_public_and_loopback_addresses() -> None:
    assert _private_ipv4_candidates(["127.0.0.1", "8.8.8.8", "192.168.1.40"]) == [
        "192.168.1.40"
    ]


def test_hostname_normalization_matches_browser_host_headers() -> None:
    assert _canonical_hostname("Harrys-MacBook-Pro.") == "harrys-macbook-pro"
