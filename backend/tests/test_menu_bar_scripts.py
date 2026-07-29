"""Tests for the non-terminal pairing output used by the macOS launcher."""

from __future__ import annotations

import sys
from typing import Any

import pytest

from scripts import run_menu_bar_service
from scripts.show_pairing_qr import parse_args


def test_menu_bar_pairing_output_flag_is_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "argv", ["show_pairing_qr.py", "--print-primary-url"])

    assert parse_args().print_primary_url is True


def test_menu_bar_pairing_flag_cannot_mix_with_allowed_hosts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        ["show_pairing_qr.py", "--print-primary-url", "--print-allowed-hosts"],
    )

    with pytest.raises(SystemExit):
        parse_args()


def test_menu_bar_reuses_only_a_successful_local_vlc_status_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Response:
        status = 200

        def __enter__(self) -> Response:
            return self

        def __exit__(self, *args: Any) -> None:
            return None

    monkeypatch.setattr(
        run_menu_bar_service, "load_vlc_http_password", lambda: "secret"
    )
    monkeypatch.setattr(
        run_menu_bar_service, "urlopen", lambda request, timeout: Response()
    )

    assert run_menu_bar_service.local_vlc_http_is_reusable() is True


def test_menu_bar_does_not_reuse_vlc_without_its_private_password(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(run_menu_bar_service, "load_vlc_http_password", lambda: None)

    assert run_menu_bar_service.local_vlc_http_is_reusable() is False
