"""Tests for the non-terminal pairing output used by the macOS launcher."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path
from typing import Any

import pytest

from scripts import launch_vlc_http, run_menu_bar_service
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


def test_menu_bar_adds_common_node_paths_for_dock_launches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PATH", "/usr/bin:/bin")
    monkeypatch.setattr(shutil, "which", lambda name: "/usr/local/bin/npm")

    assert run_menu_bar_service.configure_node_path() == "/usr/local/bin/npm"
    assert run_menu_bar_service.NODE_BIN_DIRECTORIES[0] == Path("/usr/local/bin")
    assert run_menu_bar_service.NODE_BIN_DIRECTORIES[1] == Path("/opt/homebrew/bin")


def test_menu_bar_uses_a_distinct_exit_code_for_running_vlc() -> None:
    assert run_menu_bar_service.VLC_ALREADY_RUNNING_EXIT_CODE == 12


def test_vlc_launch_uses_native_fullscreen_mode() -> None:
    command = launch_vlc_http.vlc_launch_command("private-password")

    assert "--macosx-nativefullscreenmode" in command
    assert "--macosx-continue-playback=0" in command
