# VLC HTTP compatibility

## Verification status

Live VLC HTTP verification is **pending**. VLC is installed, but its HTTP
interface was not listening during Phase 0 and neither `VLC_HTTP_BASE_URL` nor
`VLC_HTTP_PASSWORD` was configured in the shell. No playback command has been
claimed as successfully tested.

This document separates facts observed from the installed application from
behaviour that still needs a live VLC session.

## Environment inspected

| Item | Observed value | Evidence |
| --- | --- | --- |
| macOS | 14.8.5 (build 23J423) | `sw_vers` |
| Architecture | Apple silicon (`arm64`) | VLC executable file metadata |
| VLC | 3.0.23 Vetinari | VLC `--version` and app bundle metadata |
| Python | 3.12.10 | `python3 --version` |
| Node.js | 22.14.0 | `node --version` |
| npm | 10.9.2 | `npm --version` |
| Git | 2.49.0 | `git --version` |

VLC's local advanced help advertises the Lua HTTP options
`--http-password`, `--http-src`, `--http-host`, and `--http-port`.

## Installed interface contract

The installed VLC bundle contains its HTTP interface at:

```text
/Applications/VLC.app/Contents/MacOS/share/lua/http
```

The local interface documentation identifies
`/requests/status.json` as the status and command endpoint. Parameters are
URL-encoded. The anticipated authentication shape is HTTP Basic authentication
with an empty username and the configured VLC HTTP password. Authentication
must still be confirmed against the running interface.

The following table records only local documentation evidence. “Documented”
does not mean manually verified.

| Operation | Request query documented by installed VLC | Phase 0 result |
| --- | --- | --- |
| Status | no command, `GET /requests/status.json` | Documented; live request unavailable |
| Toggle pause | `command=pl_pause` | Documented; unverified |
| Resume | `command=pl_forceresume` | Documented; unverified |
| Deterministic pause | `command=pl_forcepause` | Documented; unverified |
| Stop | `command=pl_stop` | Documented; unverified |
| Previous / next | `command=pl_previous` / `pl_next` | Documented; unverified |
| Relative seek | `command=seek&val=-10S` or `+10S` | Documented; unverified |
| Absolute seek | `command=seek&val=1800` | Documented; unverified |
| Volume | `command=volume&val=70%` | Documented; unverified |
| Playback rate | `command=rate&val=1.25` | Documented; unverified |
| Audio track | `command=audio_track&val=<stream-number>` | Documented; unverified |
| Subtitle track | `command=subtitle_track&val=<stream-number>` | Documented; unverified |
| Fullscreen toggle | `command=fullscreen` | Documented; unverified |

The bundled web client converts raw VLC volume values using 256 as nominal
100% for its textual display. Phase 2 must confirm the actual response range
before finalizing the backend's percentage conversion.

## Safe status probe

On 2026-07-28, a two-second request to:

```text
http://127.0.0.1:8080/requests/status.json
```

failed with connection refused (`curl` exit code 7 / HTTP code 000). This
indicates that no HTTP service was listening at the default address at that
time. It does not establish whether VLC's password or interface preferences are
correct.

No state-changing command was sent.

## Diagnostic harness

Run the default, non-destructive status check after enabling VLC's HTTP
interface:

```bash
VLC_HTTP_BASE_URL=http://127.0.0.1:8080 \
VLC_HTTP_PASSWORD='your-vlc-http-password' \
python3 scripts/check_vlc.py
```

The script:

- never prints the password;
- distinguishes authentication, connection, HTTP, and malformed-response
  failures;
- saves structurally useful but redacted JSON under a mode-0700 temporary
  directory;
- exits non-zero when the check fails.

State-changing compatibility checks require both explicit flags and
user-controlled test media:

```bash
VLC_HTTP_BASE_URL=http://127.0.0.1:8080 \
VLC_HTTP_PASSWORD='your-vlc-http-password' \
python3 scripts/check_vlc.py \
  --integration-test \
  --confirm-test-media-loaded
```

Use optional track IDs only when the IDs are known from the running VLC
instance. Add `--test-fullscreen` only when toggling the Mac's VLC window twice
is acceptable. The integration suite stops playback at the end.

## Known limitations and implementation consequences

- The installed app is compatible with the requested Python and Node baseline.
- Live authentication shape, response fields, volume conversion, command
  idempotence, and error bodies remain unverified.
- Track selection is documented in terms of stream numbers, but the exact
  fields needed to discover stable IDs have not been observed. Track-selection
  capabilities must default to false until fixtures or live evidence exist.
- Fullscreen is documented as a toggle rather than a deterministic setter.
  The Version 1 API must not expose it until live behaviour and a safe
  capability rule are established.
- Mute is not listed as a deterministic HTTP command in the installed interface
  documentation. The planned backend process-state fallback remains necessary
  unless live testing establishes a better mechanism.
- The default port was closed during inspection, so Phase 2 should be built and
  tested with mocked responses before any live verification.

## Live verification record

Fill this section only after successful real-VLC checks.

| Date | VLC version | Media type | Command | Exact request shape | Relevant response fields | Result / limitation |
| --- | --- | --- | --- | --- | --- | --- |
| Pending | 3.0.23 | User-controlled test media | Status | `/requests/status.json` | Pending | Not run |

Redacted fixture files derived from a real response must be reviewed before
being copied into `backend/tests/fixtures`; the temporary diagnostics directory
is not part of the repository.
