# VLC HTTP compatibility

## Verification status

Live VLC HTTP status verification is available through a safe, temporary
command-line launch override. On 2026-07-29, a separate VLC 3.0.23 instance
was started with `--extraintf=http`, `--http-host=127.0.0.1`, and a one-time
password. It listened on `127.0.0.1:8080` and successfully returned an
authenticated, read-only status response. The test instance was then stopped.

Normal VLC preferences remain unsuitable for this feature: enabling **Web** in
the installed VLC 3.0.23 preferences caused normal launches to exit. The remote
therefore uses the command-line override and never turns on the Web preference.
No state-changing playback command has been claimed as successfully tested.

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

## VLC 3.0.23 launch incompatibility

On 2026-07-29, the following behavior was reproduced on the installed build:

1. Enabling **Web** in VLC preferences saved `extraintf=lua:http` in `vlcrc`.
2. A normal VLC launch briefly created its main window and then exited cleanly.
3. Launching with an empty extra-interface override kept VLC open, isolating
   the saved extra-interface value as the cause.
4. Turning off the basic **Web** checkbox left `extraintf=lua`.
5. Clearing **Interface → Main interfaces → Extra interface modules** removed
   the active `extraintf` entry.
6. VLC then opened normally without a command-line override and remained
   running. Nothing was listening on TCP port 8080.

Do not enable **Web** or **Lua interpreter** in saved VLC preferences on this
installation. Use `make vlc-http` to launch VLC with the verified temporary
override instead.

To recover if VLC starts exiting immediately:

1. Launch VLC once with an empty extra-interface override:

   ```bash
   open -na /Applications/VLC.app --args --extraintf=
   ```

2. Open **VLC media player → Settings…**, select **Show settings: All**, then
   open **Interface → Main interfaces**.
3. Turn off **Web** and **Lua interpreter**, clear **Extra interface modules**,
   and save.
4. Quit that recovery instance and open VLC normally.

## Diagnostic harness

After starting VLC through `make vlc-http`, run the default, non-destructive
status check with:

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
- The current GUI Web/Lua configuration prevents VLC from remaining open.
  `make vlc-http` bypasses that setting with a process-only override, so it must
  be used whenever live control is needed.

## Live verification record

Fill this section only after successful real-VLC checks.

| Date | VLC version | Media type | Command | Exact request shape | Relevant response fields | Result / limitation |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-07-29 | 3.0.23 | None | Launch with Web enabled | N/A | N/A | VLC exited; setting reverted |
| 2026-07-29 | 3.0.23 | None | Status | `GET /requests/status.json`, HTTP Basic auth with empty username, loopback only | `state=stopped`, `time=0/0`, `version=3.0.23 Vetinari`, `apiversion=3` | Passed with temporary `--extraintf=http` launch; no state change |
| Pending | 3.0.23 | User-controlled test media | Playback commands | Pending | Pending | Requires explicit media-test consent |

Redacted fixture files derived from a real response must be reviewed before
being copied into `backend/tests/fixtures`; the temporary diagnostics directory
is not part of the repository.
