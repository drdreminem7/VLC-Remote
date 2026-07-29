"""Tests for the non-terminal pairing output used by the macOS launcher."""

from __future__ import annotations

import sys

import pytest

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
