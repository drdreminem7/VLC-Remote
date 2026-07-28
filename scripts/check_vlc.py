#!/usr/bin/env python3
"""Safely inspect the VLC 3.x HTTP interface.

Status is read-only and is the only request made by default. State-changing
checks require both --integration-test and --confirm-test-media-loaded.
"""

from __future__ import annotations

import argparse
import base64
import json
import math
import os
import re
import sys
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

DEFAULT_BASE_URL = "http://127.0.0.1:8080"
STATUS_PATH = "/requests/status.json"
DEFAULT_TIMEOUT_SECONDS = 3.0

JsonObject = dict[str, Any]


class DiagnosticError(Exception):
    """Base class for expected diagnostic failures."""


class ConfigurationError(DiagnosticError):
    """The local diagnostic configuration is invalid."""


class AuthenticationFailure(DiagnosticError):
    """VLC rejected the configured HTTP password."""


class ConnectionFailure(DiagnosticError):
    """The VLC HTTP endpoint could not be reached."""


class HttpFailure(DiagnosticError):
    """The VLC HTTP endpoint returned an unexpected status."""


class ResponseFailure(DiagnosticError):
    """VLC returned a response that could not be interpreted."""


@dataclass(frozen=True)
class VlcConnection:
    """Validated settings required for a VLC HTTP request."""

    base_url: str
    password: str
    timeout_seconds: float


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Check VLC's local HTTP interface. The default check only reads "
            "status and never changes playback."
        )
    )
    parser.add_argument(
        "--integration-test",
        action="store_true",
        help=(
            "run state-changing compatibility checks; requires "
            "--confirm-test-media-loaded"
        ),
    )
    parser.add_argument(
        "--confirm-test-media-loaded",
        action="store_true",
        help=(
            "confirm that user-controlled disposable media is loaded and that "
            "the suite may change playback and stop it at the end"
        ),
    )
    parser.add_argument(
        "--audio-track-id",
        help="known VLC audio stream number to re-select during integration testing",
    )
    parser.add_argument(
        "--subtitle-track-id",
        help=(
            "known VLC subtitle stream number to re-select during integration testing"
        ),
    )
    parser.add_argument(
        "--test-fullscreen",
        action="store_true",
        help=(
            "toggle fullscreen twice during integration testing; use only when "
            "the installed interface documents or advertises the command"
        ),
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=f"per-request timeout in seconds (default: {DEFAULT_TIMEOUT_SECONDS})",
    )
    return parser.parse_args(argv)


def validate_base_url(value: str) -> str:
    """Return a normalized HTTP(S) base URL without credentials or a path."""

    candidate = value.strip()
    parsed = urlsplit(candidate)
    if parsed.scheme not in {"http", "https"}:
        raise ConfigurationError("VLC_HTTP_BASE_URL must use http or https.")
    if not parsed.hostname:
        raise ConfigurationError("VLC_HTTP_BASE_URL must include a hostname.")
    if parsed.username is not None or parsed.password is not None:
        raise ConfigurationError(
            "VLC_HTTP_BASE_URL must not contain credentials; use VLC_HTTP_PASSWORD."
        )
    if parsed.query or parsed.fragment:
        raise ConfigurationError(
            "VLC_HTTP_BASE_URL must not contain a query string or fragment."
        )
    if parsed.path not in {"", "/"}:
        raise ConfigurationError(
            "VLC_HTTP_BASE_URL must be an origin without an additional path."
        )
    try:
        port = parsed.port
    except ValueError as exc:
        raise ConfigurationError("VLC_HTTP_BASE_URL contains an invalid port.") from exc
    if port is not None and not 1 <= port <= 65535:
        raise ConfigurationError("VLC_HTTP_BASE_URL port must be between 1 and 65535.")

    host = parsed.hostname
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    netloc = host
    if port is not None:
        netloc = f"{netloc}:{port}"
    return urlunsplit((parsed.scheme, netloc, "", "", ""))


def load_connection(timeout_seconds: float) -> VlcConnection:
    if not math.isfinite(timeout_seconds) or not 0.1 <= timeout_seconds <= 30:
        raise ConfigurationError("--timeout must be between 0.1 and 30 seconds.")

    base_url = validate_base_url(os.environ.get("VLC_HTTP_BASE_URL", DEFAULT_BASE_URL))
    password = os.environ.get("VLC_HTTP_PASSWORD", "")
    if not password:
        raise ConfigurationError(
            "VLC_HTTP_PASSWORD is required. Set it in the environment; the "
            "diagnostic never accepts or prints it as a command-line argument."
        )
    return VlcConnection(
        base_url=base_url,
        password=password,
        timeout_seconds=timeout_seconds,
    )


def build_status_url(
    connection: VlcConnection, params: dict[str, str] | None = None
) -> str:
    query = urlencode(params or {}, safe="")
    url = f"{connection.base_url}{STATUS_PATH}"
    return f"{url}?{query}" if query else url


def request_status(
    connection: VlcConnection, params: dict[str, str] | None = None
) -> JsonObject:
    """Request and decode VLC status, translating common failures."""

    credentials = base64.b64encode(f":{connection.password}".encode()).decode("ascii")
    request = Request(
        build_status_url(connection, params),
        headers={
            "Accept": "application/json",
            "Authorization": f"Basic {credentials}",
            "User-Agent": "mac-vlc-remote-compatibility-check/0.1",
        },
        method="GET",
    )

    try:
        with urlopen(request, timeout=connection.timeout_seconds) as response:
            body = response.read()
    except HTTPError as exc:
        if exc.code in {401, 403}:
            raise AuthenticationFailure(
                "VLC rejected the HTTP password (HTTP "
                f"{exc.code}). Check VLC's web-interface password."
            ) from None
        raise HttpFailure(
            f"VLC returned HTTP {exc.code} for the status endpoint."
        ) from None
    except (URLError, TimeoutError, ConnectionError) as exc:
        reason = getattr(exc, "reason", exc)
        raise ConnectionFailure(
            "Could not connect to VLC's HTTP interface. Check that VLC is "
            f"running, the web interface is enabled, and {connection.base_url} "
            f"is correct ({type(reason).__name__})."
        ) from None

    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ResponseFailure(
            "VLC responded, but status was not valid UTF-8 JSON."
        ) from exc
    if not isinstance(payload, dict):
        raise ResponseFailure("VLC status JSON must contain an object at its root.")
    return payload


PRIVATE_KEY_PARTS = {
    "authorization",
    "password",
    "token",
    "secret",
}
MEDIA_KEY_PARTS = {
    "album",
    "artist",
    "arturl",
    "filename",
    "location",
    "name",
    "path",
    "publisher",
    "title",
    "trackid",
    "uri",
    "url",
}


def redact_json(value: Any, *, password: str) -> Any:
    """Redact credentials, local paths, URLs, and identifying media metadata."""

    if isinstance(value, dict):
        redacted: JsonObject = {}
        for key, item in value.items():
            normalized_key = re.sub(r"[^a-z0-9]", "", str(key).lower())
            if any(part in normalized_key for part in PRIVATE_KEY_PARTS):
                redacted[str(key)] = "<redacted-secret>"
            elif any(part == normalized_key for part in MEDIA_KEY_PARTS):
                redacted[str(key)] = "<redacted-media>"
            else:
                redacted[str(key)] = redact_json(item, password=password)
        return redacted
    if isinstance(value, list):
        return [redact_json(item, password=password) for item in value]
    if isinstance(value, str):
        result = value.replace(password, "<redacted-secret>") if password else value
        result = re.sub(r"file://[^\r\n\"']+", "<redacted-file-uri>", result)
        result = re.sub(r"/Users/[^/\s]+", "/Users/<redacted-user>", result)
        return result
    return value


def create_diagnostics_directory() -> Path:
    directory = Path(tempfile.mkdtemp(prefix="mac-vlc-remote-diagnostics-"))
    directory.chmod(0o700)
    return directory


def save_redacted_response(
    directory: Path, label: str, payload: JsonObject, *, password: str
) -> Path:
    destination = directory / f"{label}.json"
    destination.write_text(
        json.dumps(redact_json(payload, password=password), indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    destination.chmod(0o600)
    return destination


def find_numeric(payload: JsonObject, *keys: str) -> float | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)) and math.isfinite(float(value)):
            return float(value)
        if isinstance(value, str):
            try:
                parsed = float(value)
            except ValueError:
                continue
            if math.isfinite(parsed):
                return parsed
    return None


def describe_status(payload: JsonObject) -> str:
    state = payload.get("state", "unknown")
    version = payload.get("version", "not reported")
    api_version = payload.get("apiversion", "not reported")
    elapsed = find_numeric(payload, "time")
    duration = find_numeric(payload, "length")
    time_summary = (
        f", time={int(elapsed)}s/{int(duration)}s"
        if elapsed is not None and duration is not None
        else ""
    )
    return (
        f"state={state!s}{time_summary}, VLC version={version!s}, "
        f"HTTP API={api_version!s}"
    )


def command_params(command: str, value: str | None = None) -> dict[str, str]:
    params = {"command": command}
    if value is not None:
        params["val"] = value
    return params


def run_integration_suite(
    connection: VlcConnection,
    diagnostics: Path,
    baseline: JsonObject,
    args: argparse.Namespace,
) -> list[str]:
    """Run an explicitly authorized state-changing compatibility sequence."""

    failures: list[str] = []
    response_only: list[str] = []

    def run(
        label: str,
        command: str,
        value: str | None = None,
        verify: Callable[[JsonObject], tuple[bool, str]] | None = None,
    ) -> JsonObject | None:
        try:
            response = request_status(connection, command_params(command, value))
            save_redacted_response(
                diagnostics, label, response, password=connection.password
            )
            if verify is None:
                response_only.append(label)
                print(
                    f"RESPONSE {label}: HTTP request returned status; manual "
                    f"observation is still required ({describe_status(response)})"
                )
            else:
                verified, message = verify(response)
                if not verified:
                    failures.append(f"{label}: {message}")
                    print(f"FAIL {label}: {message}", file=sys.stderr)
                else:
                    print(f"PASS {label}: {message}")
            return response
        except DiagnosticError as exc:
            failures.append(f"{label}: {exc}")
            print(f"FAIL {label}: {exc}", file=sys.stderr)
            return None

    elapsed = find_numeric(baseline, "time") or 0
    duration = find_numeric(baseline, "length")
    volume = find_numeric(baseline, "volume")
    rate = find_numeric(baseline, "rate")

    def state_is(expected: str) -> Callable[[JsonObject], tuple[bool, str]]:
        def verify(payload: JsonObject) -> tuple[bool, str]:
            observed = str(payload.get("state", "unknown")).lower()
            return (
                observed == expected,
                f"expected state {expected!r}; observed {observed!r}",
            )

        return verify

    def numeric_is_close(
        key: str, expected: float, tolerance: float
    ) -> Callable[[JsonObject], tuple[bool, str]]:
        def verify(payload: JsonObject) -> tuple[bool, str]:
            observed = find_numeric(payload, key)
            if observed is None:
                return False, f"response did not report numeric {key!r}"
            return (
                abs(observed - expected) <= tolerance,
                f"expected {key} near {expected:g}; observed {observed:g}",
            )

        return verify

    run("pause", "pl_forcepause", verify=state_is("paused"))
    resumed = run("resume", "pl_forceresume", verify=state_is("playing"))
    resumed_time = find_numeric(resumed or baseline, "time") or elapsed

    backward_target = max(0, resumed_time - 10)
    backward = run(
        "seek_backward_10s",
        "seek",
        "-10S",
        verify=numeric_is_close("time", backward_target, 4),
    )
    backward_time = find_numeric(backward or {}, "time")
    forward_target = (
        backward_time if backward_time is not None else backward_target
    ) + 10
    if duration is not None:
        forward_target = min(forward_target, duration)
    run(
        "seek_forward_10s",
        "seek",
        "+10S",
        verify=numeric_is_close("time", forward_target, 4),
    )
    run(
        "seek_absolute",
        "seek",
        str(max(0, int(elapsed))),
        verify=numeric_is_close("time", max(0, int(elapsed)), 4),
    )

    if volume is None:
        failures.append("volume: baseline status did not report a numeric volume")
        print(
            "SKIP volume: baseline status did not report a numeric volume",
            file=sys.stderr,
        )
    else:
        # Lower volume temporarily so the check never makes playback louder,
        # then restore the exact observed raw value.
        test_volume = max(0, int(volume) - 13)
        changed_volume = run(
            "volume_change",
            "volume",
            str(test_volume),
            verify=numeric_is_close("volume", test_volume, 2),
        )
        if changed_volume is not None:
            run(
                "volume_restore",
                "volume",
                str(max(0, int(volume))),
                verify=numeric_is_close("volume", max(0, int(volume)), 2),
            )

    if rate is None or rate <= 0:
        failures.append("rate: baseline status did not report a positive rate")
        print(
            "SKIP rate: baseline status did not report a positive rate",
            file=sys.stderr,
        )
    else:
        test_rate = 1.1 if abs(rate - 1.1) > 0.01 else 1.0
        changed_rate = run(
            "rate_change",
            "rate",
            f"{test_rate:g}",
            verify=numeric_is_close("rate", test_rate, 0.02),
        )
        if changed_rate is not None:
            run(
                "rate_restore",
                "rate",
                f"{rate:g}",
                verify=numeric_is_close("rate", rate, 0.02),
            )

    if args.audio_track_id is not None:
        run("audio_track", "audio_track", args.audio_track_id)
    else:
        print("SKIP audio_track: pass a known --audio-track-id to test selection")

    if args.subtitle_track_id is not None:
        run("subtitle_track", "subtitle_track", args.subtitle_track_id)
    else:
        print("SKIP subtitle_track: pass a known --subtitle-track-id to test selection")

    run("playlist_next", "pl_next")
    run("playlist_previous", "pl_previous")

    if args.test_fullscreen:
        first_toggle = run("fullscreen_on_toggle", "fullscreen")
        if first_toggle is not None:
            run("fullscreen_restore_toggle", "fullscreen")
    else:
        print(
            "SKIP fullscreen: pass --test-fullscreen only when the command is "
            "documented or advertised"
        )

    # The specification asks the integration harness to test stop. Keep this
    # last because it intentionally leaves the user's test media stopped.
    run("stop", "pl_stop", verify=state_is("stopped"))
    if response_only:
        print(
            "Manual observation is still required for commands whose response "
            f"does not expose a reliable outcome: {', '.join(response_only)}."
        )
    return failures


def exit_code_for(error: DiagnosticError) -> int:
    if isinstance(error, ConfigurationError):
        return 2
    if isinstance(error, AuthenticationFailure):
        return 3
    if isinstance(error, ConnectionFailure):
        return 4
    if isinstance(error, (HttpFailure, ResponseFailure)):
        return 5
    return 1


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        connection = load_connection(args.timeout)
        if args.confirm_test_media_loaded and not args.integration_test:
            raise ConfigurationError(
                "--confirm-test-media-loaded has no effect without --integration-test."
            )
        if args.integration_test and not args.confirm_test_media_loaded:
            raise ConfigurationError(
                "--integration-test changes VLC state and requires "
                "--confirm-test-media-loaded."
            )
        if (
            args.audio_track_id is not None
            or args.subtitle_track_id is not None
            or args.test_fullscreen
        ) and not args.integration_test:
            raise ConfigurationError(
                "Track and fullscreen checks require --integration-test."
            )

        diagnostics = create_diagnostics_directory()
        print(f"Diagnostics directory: {diagnostics}")
        print("Requesting non-destructive VLC status...")
        baseline = request_status(connection)
        status_path = save_redacted_response(
            diagnostics, "status", baseline, password=connection.password
        )
        print(f"PASS status: {describe_status(baseline)}")
        print(f"Saved redacted status: {status_path}")

        if not args.integration_test:
            print("No state-changing commands were sent.")
            return 0

        state = str(baseline.get("state", "unknown")).lower()
        duration = find_numeric(baseline, "length")
        if state in {"stopped", "stop", "unknown"} or duration is None or duration <= 0:
            raise ConfigurationError(
                "The integration suite requires loaded test media with a "
                "positive duration and a known playing or paused state."
            )

        print(
            "Starting explicitly authorized integration checks. Playback state "
            "will change and media will be stopped at the end."
        )
        failures = run_integration_suite(connection, diagnostics, baseline, args)
        if failures:
            print(
                f"Integration checks completed with {len(failures)} failure(s).",
                file=sys.stderr,
            )
            return 6
        print(
            "All automatically verifiable checks passed and all remaining "
            "requested HTTP calls returned. Review the RESPONSE lines before "
            "recording manual compatibility."
        )
        return 0
    except DiagnosticError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return exit_code_for(exc)
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
