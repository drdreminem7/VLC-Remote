# Mac VLC Remote — Complete Codex Implementation Specification

## 1. Project summary

Build a secure, mobile-first web application that lets a phone control VLC Media Player running on a Mac.

The application runs locally on the Mac and is accessed from the phone through Safari or another mobile browser while both devices are connected to the same trusted network.

The completed application must support:

- Viewing current VLC playback status.
- Play and pause.
- Seeking backward and forward.
- Seeking to an exact position using a timeline.
- Changing volume.
- Muting and unmuting.
- Changing playback speed where supported.
- Displaying the current media title and playback time.
- Selecting subtitles and audio tracks where supported.
- Installing the interface on the phone as a Progressive Web App.
- Secure authentication between the phone and Mac.
- Clear setup and troubleshooting instructions.
- Automated tests that do not require VLC to be running.
- A manual integration-test procedure for a real VLC installation.

The project should be usable, maintainable and suitable for a software-engineering portfolio.

---

# 2. Core product decisions

## 2.1 Application model

Use this architecture:

```text
Mobile browser / installed PWA
             |
             | HTTP requests over local network
             v
FastAPI application running on Mac
             |
             | Authenticated local HTTP requests
             v
VLC HTTP control interface on localhost
```

The browser must never communicate directly with VLC.

Only the FastAPI backend may know:

- The VLC HTTP password.
- The VLC HTTP address.
- The remote-control access token.
- Internal VLC command details.

## 2.2 Technology stack

### Backend

Use:

- Python 3.11 or newer.
- FastAPI.
- Uvicorn.
- HTTPX.
- Pydantic and pydantic-settings.
- Pytest.
- pytest-asyncio.
- respx or an equivalent HTTPX mocking library.
- Ruff for linting and formatting.
- mypy for static type checking.

### Frontend

Use:

- React.
- TypeScript.
- Vite.
- Responsive CSS without a heavy component framework.
- Vitest.
- React Testing Library.
- Playwright for end-to-end browser testing.
- A maintained Vite-compatible PWA solution.

Use stable package versions available at implementation time and commit the lock file.

### Supporting tools

Use:

- Git.
- Makefile commands for common tasks.
- A shell setup script for macOS.
- QR-code generation for easy phone pairing.
- Optional Bonjour/mDNS service advertisement if it can be implemented reliably without making installation fragile.

## 2.3 Explicit non-goals

Version 1 must not:

- Stream the movie from the Mac to the phone.
- Upload or browse arbitrary Mac files.
- Execute arbitrary terminal commands.
- Accept arbitrary AppleScript from the browser.
- Expose VLC directly to the internet.
- Require a native iOS application.
- Require an App Store account.
- Require a cloud backend.
- Require an external database.
- Collect analytics.
- load third-party scripts into the frontend.
- support multiple Mac users simultaneously.
- attempt to wake a fully powered-off Mac.

Remote access outside the home network is a later optional feature and must use a private-network solution such as Tailscale rather than public router port forwarding.

---

# 3. User stories

## 3.1 Initial setup

As the user, I can:

1. Install backend and frontend dependencies.
2. Configure VLC’s HTTP interface and password.
3. Start the remote application with one documented command.
4. See whether the backend can connect to VLC.
5. See the address I should open on my phone.
6. Scan a QR code instead of manually typing an address and access token.
7. Understand any setup error from a useful error message.

## 3.2 Normal playback

As the user, I can:

- See the current media title.
- See whether VLC is playing, paused or stopped.
- See elapsed and total time.
- Tap a large play/pause button.
- Seek backward by 10 seconds.
- Seek backward by 30 seconds.
- Seek forward by 10 seconds.
- Seek forward by 30 seconds.
- Drag a timeline to another point in the film.
- Increase or decrease volume.
- Mute or restore volume.
- Change playback speed.
- See when the phone has lost connection with the Mac.
- See when the backend is reachable but VLC is not.

## 3.3 Advanced media controls

Where supported by the installed VLC HTTP interface, I can:

- Select a subtitle track.
- Disable subtitles.
- Select an audio track.
- Move to the next playlist item.
- Move to the previous playlist item.
- Stop playback.
- Toggle fullscreen.

Unsupported controls must be disabled or hidden based on backend-reported capabilities. The frontend must not pretend that a command succeeded.

---

# 4. Security model

## 4.1 Threat model

Version 1 is intended for a trusted home or private network.

It must still prevent another person on the network from controlling VLC simply by discovering the Mac’s address.

It does not promise protection against a malicious network administrator capable of intercepting unencrypted local HTTP traffic. HTTPS or a private encrypted network can be added later.

## 4.2 Browser authentication

Use a randomly generated bearer token.

Requirements:

- Generate at least 32 random bytes using a cryptographically secure generator.
- Store the token in a configuration file under the user’s home directory.
- Apply file permissions that limit the file to the current macOS user where possible.
- Never commit the token.
- Never place it in `.env.example`.
- Never print it in normal application logs.
- Compare tokens using a constant-time comparison.
- Require it for every `/api/v1/*` route except the public health endpoint if one exists.

## 4.3 QR-code pairing

The startup command should display a QR code pointing to an address similar to:

```text
http://mac-hostname.local:8000/#token=<generated-token>
```

The token must be placed in the URL fragment after `#`, not in the server-side URL query.

Frontend behaviour:

1. Read the token from the URL fragment.
2. Save it locally on the phone.
3. Immediately remove it from the visible address using `history.replaceState`.
4. Send it in the `Authorization` header:

```http
Authorization: Bearer <token>
```

5. Provide a “Forget this Mac” control that removes the stored token.

Do not include tokens in:

- Query strings.
- Server logs.
- Error-reporting output.
- HTML generated by the backend.
- Git files.

## 4.4 Backend restrictions

The backend must:

- Expose only predefined VLC operations.
- Never accept arbitrary VLC command names from the frontend.
- Never accept terminal commands.
- Never accept AppleScript source text.
- Validate all numerical values.
- Reject malformed JSON.
- Apply short VLC request timeouts.
- Use POST for state-changing operations.
- Avoid wildcard CORS.
- Serve frontend and API from the same origin.
- Limit accepted hostnames where reasonably practical.
- Avoid returning internal passwords or exception traces.
- Avoid logging request authorization headers.

## 4.5 VLC exposure

Configure VLC so that its HTTP interface is reachable only from the Mac itself where supported:

```text
127.0.0.1
```

The FastAPI application is the network-facing layer.

The VLC password is read from backend configuration and must never reach the browser.

---

# 5. Repository layout

Create this structure:

```text
mac-vlc-remote/
├── AGENTS.md
├── SPEC.md
├── README.md
├── LICENSE
├── .gitignore
├── .env.example
├── Makefile
├── pyproject.toml
├── package.json
├── package-lock.json
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── dependencies.py
│   │   ├── errors.py
│   │   ├── security.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── api.py
│   │   │   └── vlc.py
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── health.py
│   │   │   ├── playback.py
│   │   │   ├── audio.py
│   │   │   └── tracks.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── vlc_client.py
│   │   │   ├── vlc_parser.py
│   │   │   ├── capabilities.py
│   │   │   └── discovery.py
│   │   └── static/
│   └── tests/
│       ├── fixtures/
│       │   ├── status_playing.json
│       │   ├── status_paused.json
│       │   ├── status_stopped.json
│       │   └── status_tracks.json
│       ├── test_auth.py
│       ├── test_health.py
│       ├── test_vlc_client.py
│       ├── test_vlc_parser.py
│       └── test_playback_api.py
├── frontend/
│   ├── index.html
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── public/
│   │   ├── icons/
│   │   └── manifest.webmanifest
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── styles.css
│   │   ├── api/
│   │   │   ├── client.ts
│   │   │   └── types.ts
│   │   ├── auth/
│   │   │   └── token.ts
│   │   ├── hooks/
│   │   │   ├── usePlaybackStatus.ts
│   │   │   └── useVisibilityPolling.ts
│   │   ├── components/
│   │   │   ├── ConnectionBanner.tsx
│   │   │   ├── MediaInformation.tsx
│   │   │   ├── PlaybackControls.tsx
│   │   │   ├── SeekBar.tsx
│   │   │   ├── VolumeControl.tsx
│   │   │   ├── SpeedControl.tsx
│   │   │   ├── TrackSelector.tsx
│   │   │   └── SettingsPanel.tsx
│   │   └── utils/
│   │       ├── formatTime.ts
│   │       └── clamp.ts
│   └── tests/
├── scripts/
│   ├── bootstrap.sh
│   ├── check_vlc.py
│   ├── run_dev.sh
│   ├── run_production.sh
│   ├── show_pairing_qr.py
│   └── install_launch_agent.sh
├── docs/
│   ├── VLC_SETUP.md
│   ├── ARCHITECTURE.md
│   ├── SECURITY.md
│   ├── TESTING.md
│   ├── TROUBLESHOOTING.md
│   └── MANUAL_TEST_CHECKLIST.md
└── .github/
    └── workflows/
        └── ci.yml
```

Codex may adjust minor paths if it records the reason in `docs/ARCHITECTURE.md`.

---

# 6. Configuration

Use backend settings with environment-variable support.

Provide `.env.example` containing only placeholders:

```dotenv
VLC_REMOTE_HOST=0.0.0.0
VLC_REMOTE_PORT=8000

VLC_HTTP_BASE_URL=http://127.0.0.1:8080
VLC_HTTP_PASSWORD=replace-me

VLC_REMOTE_ACCESS_TOKEN=
VLC_REMOTE_LOG_LEVEL=INFO
VLC_REMOTE_ALLOWED_HOSTS=localhost,127.0.0.1
VLC_REMOTE_ENABLE_DISCOVERY=true
```

Rules:

- An empty remote access token means “generate or load one from the user configuration directory.”
- Never generate a weak default VLC password.
- Never commit a real `.env`.
- Fail with a clear message if the VLC password is missing.
- Validate URLs and ports during application startup.
- Do not include sensitive settings in `/health`.

---

# 7. VLC compatibility investigation

This is Phase 0 and must happen before implementing the final `VlcClient`.

## 7.1 Purpose

Determine the exact behaviour of the HTTP interface provided by the VLC version installed on the user’s Mac.

Do not assume that every historic VLC command still works identically.

## 7.2 Investigation script

Create `scripts/check_vlc.py`.

It should:

1. Read VLC base URL and password from environment variables.
2. Request the VLC status endpoint.
3. Report authentication failure separately from connection failure.
4. Print the installed VLC version when available.
5. Save redacted example responses to a temporary diagnostics directory.
6. Test only safe, non-destructive status calls by default.
7. Offer an explicit flag for testing state-changing commands.
8. Never print the VLC password.
9. Return a non-zero exit code on failure.

With an explicit integration-test flag and user-controlled media loaded, test:

- Status.
- Pause.
- Resume.
- Relative seek backward.
- Relative seek forward.
- Absolute seek.
- Volume.
- Rate.
- Stop.
- Next and previous item.
- Subtitle-track listing and selection.
- Audio-track listing and selection.
- Fullscreen only if the interface advertises or documents it.

## 7.3 Compatibility document

Create `docs/VLC_COMPATIBILITY.md` recording:

- macOS version.
- VLC version.
- Interface endpoint used.
- Authentication method.
- Verified command.
- Exact request shape.
- Relevant response fields.
- Whether the feature is reliable.
- Any known limitation.
- Fixture files generated for automated tests.

Never claim a command was manually verified unless it was actually run successfully.

If a real VLC installation is unavailable to Codex, implement the compatibility harness and mocked client, then explicitly mark live verification as pending.

---

# 8. Backend domain model

Create normalized models that isolate the frontend from VLC’s raw response format.

## 8.1 Playback state

```typescript
type PlaybackState = "playing" | "paused" | "stopped" | "opening" | "buffering" | "unknown";
```

## 8.2 Playback status response

The normalized response should resemble:

```json
{
    "connection": {
        "backend": "online",
        "vlc": "online"
    },
    "state": "playing",
    "media": {
        "title": "Example Film",
        "filename": "example-film.mkv"
    },
    "time": {
        "elapsedSeconds": 3724,
        "durationSeconds": 7210,
        "position": 0.5165
    },
    "audio": {
        "volumePercent": 70,
        "muted": false
    },
    "playbackRate": 1.0,
    "tracks": {
        "audio": [],
        "subtitles": []
    },
    "capabilities": {
        "seek": true,
        "volume": true,
        "rate": true,
        "audioTrackSelection": false,
        "subtitleTrackSelection": false,
        "fullscreen": false,
        "playlistNavigation": true
    },
    "updatedAt": "ISO-8601 timestamp"
}
```

## 8.3 Capability handling

Capabilities must be determined from:

1. Results of the compatibility layer.
2. Available response fields.
3. Backend configuration overrides where necessary.

The frontend must use the capability response rather than assuming all features exist.

---

# 9. Backend API

Prefix all routes with:

```text
/api/v1
```

## 9.1 Health

### `GET /api/v1/health`

Return:

- Backend availability.
- Backend version.
- Whether VLC is reachable.
- No secrets.
- No VLC password.
- No access token.
- No raw exception traces.

## 9.2 Status

### `GET /api/v1/status`

Return normalized playback state.

Requirements:

- Use a short request timeout.
- Cache identical simultaneous status requests for approximately 200–500 milliseconds.
- Do not allow overlapping requests to overwhelm VLC.
- Return a structured `503` response when VLC is unavailable.
- Preserve the distinction between backend failure and VLC failure.

## 9.3 Playback commands

### `POST /api/v1/playback/toggle`

Toggle play/pause.

### `POST /api/v1/playback/play`

Play or resume where reliably supported.

### `POST /api/v1/playback/pause`

Pause where reliably supported.

### `POST /api/v1/playback/stop`

Stop playback.

### `POST /api/v1/playback/seek`

Request body:

```json
{
    "mode": "relative",
    "seconds": -10
}
```

or:

```json
{
    "mode": "absolute",
    "seconds": 1800
}
```

Validation:

- Relative seek must be within a conservative configured range, such as ±3,600 seconds.
- Absolute seek cannot be negative.
- Reject NaN, infinity, strings and malformed values.
- Clamp absolute seek to known duration where sensible.
- Return updated normalized status after success.

### `POST /api/v1/playback/rate`

```json
{
    "rate": 1.25
}
```

Use a conservative allowed range, such as `0.25` to `4.0`, unless live compatibility testing establishes a narrower range.

### `POST /api/v1/playback/next`

Move to next playlist item where supported.

### `POST /api/v1/playback/previous`

Move to previous playlist item where supported.

### `POST /api/v1/playback/fullscreen`

Expose only if verified.

## 9.4 Audio commands

### `POST /api/v1/audio/volume`

```json
{
    "percent": 70
}
```

Validate a supported range.

Do not assume raw VLC volume units equal percentages. Put conversion logic in the VLC adapter.

### `POST /api/v1/audio/mute`

```json
{
    "muted": true
}
```

If VLC lacks a deterministic mute command, preserve the previous non-zero volume inside backend process state and document the limitation.

## 9.5 Track selection

### `POST /api/v1/tracks/subtitle`

```json
{
    "trackId": "string-or-number-from-normalized-status"
}
```

Support a normalized “off” selection.

### `POST /api/v1/tracks/audio`

```json
{
    "trackId": "string-or-number-from-normalized-status"
}
```

Reject IDs that are not present in the latest known track list where possible.

## 9.6 Standard error shape

Use one consistent structure:

```json
{
    "error": {
        "code": "VLC_UNAVAILABLE",
        "message": "The remote service is running, but VLC could not be reached.",
        "retryable": true,
        "details": null
    }
}
```

Expected codes include:

- `UNAUTHORIZED`
- `INVALID_REQUEST`
- `UNSUPPORTED_OPERATION`
- `VLC_UNAVAILABLE`
- `VLC_AUTHENTICATION_FAILED`
- `VLC_COMMAND_FAILED`
- `INTERNAL_ERROR`

---

# 10. VLC adapter

Create a `VlcClient` interface or protocol.

Required operations:

```python
class VlcClientProtocol(Protocol):
    async def get_status(self) -> VlcStatus: ...
    async def toggle_playback(self) -> VlcStatus: ...
    async def play(self) -> VlcStatus: ...
    async def pause(self) -> VlcStatus: ...
    async def stop(self) -> VlcStatus: ...
    async def seek_relative(self, seconds: int) -> VlcStatus: ...
    async def seek_absolute(self, seconds: int) -> VlcStatus: ...
    async def set_volume(self, percent: int) -> VlcStatus: ...
    async def set_rate(self, rate: float) -> VlcStatus: ...
    async def select_audio_track(self, track_id: str) -> VlcStatus: ...
    async def select_subtitle_track(self, track_id: str) -> VlcStatus: ...
    async def next_item(self) -> VlcStatus: ...
    async def previous_item(self) -> VlcStatus: ...
```

Implementation requirements:

- Use one reusable `httpx.AsyncClient`.
- Use HTTP Basic Authentication according to the verified VLC setup.
- Use explicit connect, read, write and pool timeouts.
- Translate HTTPX exceptions into application-specific exceptions.
- Never expose raw credentials.
- Keep raw VLC parsing separate from API models.
- Add fixture-driven parsing tests.
- URL-encode command parameters correctly.
- Do not build request URLs by unsafe string concatenation.
- Support dependency injection so tests can use `FakeVlcClient`.

---

# 11. Frontend requirements

## 11.1 General layout

Use a single-column mobile-first interface.

Approximate layout:

```text
┌──────────────────────────────┐
│ Connection status            │
│                              │
│ Film title                   │
│ 01:02:04 / 02:01:10          │
│                              │
│ ━━━━━━━━━●━━━━━━━━━━━━━━━━   │
│                              │
│     -30     -10     +10      │
│                              │
│          PLAY / PAUSE        │
│                              │
│ Volume slider        Mute    │
│ Playback speed               │
│ Subtitles                    │
│ Audio track                  │
│                              │
│ Settings                     │
└──────────────────────────────┘
```

## 11.2 Touch requirements

- Primary touch controls should be at least approximately 44×44 CSS pixels.
- Avoid controls packed tightly together.
- Disable accidental text selection on control buttons.
- Use visible pressed, disabled and loading states.
- Respect iPhone safe-area insets.
- Do not rely only on colour to convey status.

## 11.3 Playback polling

Initial implementation should use HTTP polling rather than WebSockets.

Rules:

- Poll approximately every 750–1,000 milliseconds while the page is visible.
- Poll less frequently while the page is hidden.
- Pause or reduce polling when the browser is offline.
- Use exponential backoff after repeated failures.
- Reset backoff after recovery.
- Abort stale requests.
- Never start multiple simultaneous polling loops.
- Optimistically update controls only when rollback behaviour is clear.
- Refresh status immediately after a successful command.

## 11.4 Timeline behaviour

The seek bar must:

- Display current position.
- Show preview time while dragging.
- Avoid sending a command for every pointer movement.
- Send the final absolute seek when the drag ends.
- Remain usable when duration is unknown.
- Avoid jumping underneath the user while they are dragging.
- Re-synchronise with VLC after the command completes.

## 11.5 Connection states

Represent at least:

1. Connecting to backend.
2. Backend online and VLC online.
3. Backend online but VLC unavailable.
4. Authentication rejected.
5. Phone offline.
6. General server error.

Messages must explain the likely next action.

Examples:

- “Remote service found, but VLC is not responding.”
- “Check that VLC is open and its HTTP interface is enabled.”
- “This phone is not paired with the Mac.”
- “The Mac remote cannot be reached on this network.”

## 11.6 Accessibility

- Use semantic buttons.
- Include accessible names.
- Support keyboard interaction for desktop testing.
- Maintain visible focus indicators.
- Use sufficient contrast.
- Mark status messages appropriately for assistive technology.
- Provide text equivalents for icons.
- Do not place essential information only in animations.

## 11.7 PWA

Implement:

- Web app manifest.
- App name and short name.
- Home-screen icons.
- Standalone display mode.
- Theme and background metadata.
- Basic service worker.
- Cached application shell.
- Clear “Mac unavailable” state when the UI is cached but API calls fail.
- No attempt to cache API command responses.
- Version strategy that avoids permanently serving stale UI.

---

# 12. Startup and setup experience

## 12.1 Bootstrap command

Provide:

```bash
make bootstrap
```

It should:

- Check for Python.
- Check for Node.js.
- Create a Python virtual environment.
- Install backend dependencies.
- Install frontend dependencies.
- Build the frontend where appropriate.
- Create necessary local configuration directories.
- Avoid overwriting existing secrets.
- Print clear next steps.

Do not automatically change VLC preferences without explicit permission.

## 12.2 Development command

Provide:

```bash
make dev
```

This may run backend and frontend development servers separately.

Document any development-only CORS setup and ensure production does not use permissive CORS.

## 12.3 Production-like local command

Provide:

```bash
make run
```

It should:

1. Build the frontend.
2. Copy or expose built static assets to FastAPI.
3. Start one FastAPI/Uvicorn service.
4. Display the local phone URL.
5. Display the pairing QR code.
6. Show whether VLC passed the connectivity check.
7. Avoid printing secrets as plain text beyond the QR code’s intentional first-time pairing representation.

## 12.4 macOS background service

After the main application is complete, optionally provide a LaunchAgent installer.

Requirements:

- Installation must be explicit.
- Include uninstall instructions.
- Store logs in a documented user directory.
- Do not run as root.
- Do not hard-code a developer-specific path.
- Explain that VLC itself may still need to be running.

This is not required for the earliest MVP.

---

# 13. Testing strategy

## 13.1 Backend unit tests

Test:

- Valid and invalid bearer tokens.
- Missing authorization.
- Redaction of sensitive values.
- VLC connection failure.
- VLC authentication failure.
- Malformed VLC status data.
- Playing, paused and stopped status parsing.
- Missing metadata.
- Unknown duration.
- Volume conversion.
- Seek validation.
- Rate validation.
- Unsupported commands.
- API error shape.
- Status-request deduplication or short caching.
- No secrets in health responses.

## 13.2 Frontend unit tests

Test:

- Time formatting.
- Playback-state rendering.
- Disabled unsupported controls.
- Seek preview.
- Token extraction from URL fragment.
- Removal of token from visible URL.
- Authentication error.
- Backend unavailable state.
- VLC unavailable state.
- Polling cleanup.
- Visibility-based polling interval.
- Button command calls.
- No seek commands during intermediate slider movement.

## 13.3 End-to-end tests

Use Playwright with a mocked backend.

Test at an iPhone-like viewport:

1. Pair using a URL fragment.
2. Load playing status.
3. Pause playback.
4. Seek backward.
5. Seek forward.
6. Drag timeline.
7. Set volume.
8. Lose backend connection.
9. Recover connection.
10. Render unsupported controls correctly.
11. Forget pairing token.

Do not require a real VLC instance in continuous integration.

## 13.4 Manual real-VLC test

Create `docs/MANUAL_TEST_CHECKLIST.md` with checkboxes for:

- VLC setup.
- Authentication.
- Phone connection.
- Play/pause.
- Relative seek.
- Absolute seek.
- Long film duration.
- Volume.
- Mute.
- Playback speed.
- Subtitle tracks.
- Audio tracks.
- Playlist navigation.
- Fullscreen if supported.
- Phone screen lock and reopen.
- Wi-Fi disconnect and reconnect.
- VLC close and reopen.
- Backend restart.
- PWA installation.
- Incorrect token.
- Second unpaired device.

## 13.5 CI

GitHub Actions should run:

```text
Backend formatting check
Backend lint
Backend type checking
Backend tests
Frontend lint
Frontend type checking
Frontend unit tests
Frontend build
Playwright tests where practical
```

No secret credentials should be required by CI.

---

# 14. Documentation deliverables

## README.md

Include:

- What the project does.
- Architecture diagram.
- Screenshot placeholder.
- Requirements.
- Quick start.
- VLC setup link.
- Development commands.
- Production-like local run.
- Phone pairing.
- Test commands.
- Security limitations.
- Troubleshooting.
- Project status.
- Licence.

## docs/VLC_SETUP.md

Include precise macOS setup instructions, but distinguish:

- Verified instructions.
- Version-dependent menu names.
- Terminal-based diagnostic commands.
- How to choose a strong VLC password.
- How to restrict VLC to localhost where possible.
- How to restart VLC after changes.

## docs/ARCHITECTURE.md

Include:

- Components.
- Request flow.
- Security boundaries.
- Raw VLC response normalization.
- Polling model.
- Configuration.
- Important trade-offs.
- Rejected alternatives.

## docs/SECURITY.md

Include:

- Threat model.
- Token storage.
- QR pairing.
- Local HTTP limitation.
- Why VLC is not exposed directly.
- Why arbitrary shell commands are forbidden.
- Remote-access guidance.
- Secret rotation.
- How to revoke phone access by rotating the token.

## docs/TROUBLESHOOTING.md

Cover:

- Phone cannot reach Mac.
- Wrong network.
- macOS firewall.
- VLC not running.
- VLC HTTP interface not enabled.
- VLC password mismatch.
- Port already in use.
- Hostname `.local` does not resolve.
- Token rejected.
- UI installed but API unavailable.
- Stale PWA assets.
- Subtitle or audio controls unsupported.

---

# 15. Definition of done

The project is complete only when:

- The repository builds from documented commands.
- `make bootstrap` works on a clean supported Mac development environment.
- `make test` runs all practical automated tests.
- `make run` serves the built application.
- The phone can authenticate with the generated pairing token.
- Play/pause works against a real compatible VLC installation.
- Relative seeking works.
- Absolute timeline seeking works.
- Volume works.
- Connection failures are clearly displayed.
- VLC credentials never appear in frontend source or API responses.
- The frontend is installable as a PWA.
- Core functionality works at a mobile viewport.
- Documentation covers setup and common failures.
- Automated tests use mocks and fixtures.
- Live-VLC verification results are documented honestly.
- Linting, type checks, tests and frontend build pass.
- Codex performs a final security review.
- Codex performs a final maintainability review.
- No known critical or high-severity issue remains unresolved.

---

# 16. Required AGENTS.md

Create the following `AGENTS.md` at repository root and update commands if implementation details change.

```markdown
# AGENTS.md

## Project

This repository contains a local, mobile-first VLC remote control for macOS.

The React frontend runs in a phone browser or as a PWA. It communicates with a
FastAPI backend. The backend communicates with VLC's localhost-only HTTP
interface.

Read `SPEC.md` before making architectural or behavioural changes.

## Primary constraints

- Never expose the VLC password to the frontend.
- Never expose arbitrary VLC commands through the API.
- Never execute browser-provided shell commands or AppleScript.
- Never commit `.env`, access tokens, passwords or generated configuration.
- State-changing operations must use POST.
- Do not use wildcard CORS in production.
- Keep the frontend and production API on the same origin.
- Do not claim that a VLC command was tested against real VLC unless it was.
- Keep all VLC-specific parsing and command mapping behind the VLC adapter.
- Automated tests must not require a running VLC instance.

## Repository structure

- `backend/app`: FastAPI application.
- `backend/tests`: backend tests and VLC fixtures.
- `frontend/src`: React and TypeScript frontend.
- `frontend/tests`: frontend tests.
- `scripts`: bootstrap, diagnostics and run scripts.
- `docs`: architecture, setup, security and testing documentation.

## Commands

Keep these commands working:

- `make bootstrap`
- `make dev`
- `make build`
- `make lint`
- `make typecheck`
- `make test`
- `make run`

If command names change, update this file and README.md in the same change.

## Backend conventions

- Use typed Python.
- Use Pydantic models for API inputs and outputs.
- Use dependency injection for the VLC client.
- Use application-specific exceptions.
- Use one reusable HTTPX async client.
- Validate all external input.
- Avoid leaking internal exception text to clients.
- Add tests for bug fixes and new behaviour.
- Format and lint with Ruff.
- Type-check with mypy.

## Frontend conventions

- Use TypeScript in strict mode.
- Use semantic, accessible HTML.
- Optimise for small phone screens first.
- Keep API access in the API client module.
- Keep token handling in the auth module.
- Do not add third-party runtime scripts.
- Do not send a seek command for every slider movement.
- Clean up polling timers and aborted requests.
- Add tests for user-visible state changes.

## Security review

For each feature, consider:

- Authentication bypass.
- Secret leakage.
- Arbitrary command injection.
- Unsafe URL handling.
- Missing input validation.
- Excessive network exposure.
- Sensitive logging.
- Cross-origin behaviour.
- PWA cache behaviour.

## Verification before completion

Run:

1. Formatting.
2. Linting.
3. Type checking.
4. Backend tests.
5. Frontend tests.
6. Frontend production build.
7. End-to-end tests where configured.

Inspect `git diff` and report:

- Files changed.
- Commands run.
- Test results.
- Manual verification performed.
- Manual verification still required.
- Remaining risks or limitations.

Do not mark work complete when a required test is failing.
```

---

# 17. Codex execution workflow

Do not ask Codex to implement the entire project in one uncontrolled pass.

Use one Git branch and one checkpoint per phase.

Before starting:

```bash
mkdir mac-vlc-remote
cd mac-vlc-remote
git init
```

Create `SPEC.md` and `AGENTS.md`, then commit them:

```bash
git add SPEC.md AGENTS.md
git commit -m "docs: define VLC remote implementation specification"
```

Open the repository in Codex.

---

# 18. Phase 0 Codex prompt — inspect and plan

```text
Read AGENTS.md and SPEC.md completely.

Do not implement the full application yet.

Perform Phase 0:

1. Inspect the repository.
2. Inspect the available macOS development environment.
3. Check Python, Node.js, npm, Git and VLC availability and versions.
4. Research the installed VLC HTTP interface using local files, VLC help output
   and safe status requests where possible.
5. Create docs/VLC_COMPATIBILITY.md.
6. Create scripts/check_vlc.py.
7. Create an implementation checklist broken into the phases from SPEC.md.
8. Identify any part of SPEC.md that is incompatible with the actual installed
   environment.
9. Do not invent successful real-VLC tests.
10. Do not make destructive system changes.
11. Run all tests that are possible for this phase.
12. Report files changed, commands run, results, blockers and recommended
    adjustments.

Keep the scope limited to investigation, diagnostics and planning.
```

After completion:

- Inspect the diff.
- Run `/review`.
- Correct serious findings.
- Commit:

```bash
git add .
git commit -m "chore: add VLC compatibility diagnostics"
```

---

# 19. Phase 1 Codex prompt — project foundation

```text
Read AGENTS.md, SPEC.md and docs/VLC_COMPATIBILITY.md.

Implement Phase 1: repository foundation only.

Create:

- Python project configuration.
- Backend package skeleton.
- Frontend Vite React TypeScript project.
- Makefile.
- .gitignore.
- .env.example.
- Basic README.
- Backend health route.
- Basic frontend application shell.
- Backend and frontend test infrastructure.
- GitHub Actions CI.
- Development and production build commands.

Requirements:

- Keep production frontend and API on the same origin.
- Do not implement raw VLC commands yet beyond a clearly isolated stub.
- Do not add wildcard production CORS.
- All specified make commands should exist.
- Add tests for the health endpoint and basic application render.
- Run formatting, linting, type checking, tests and builds.
- Fix failures before finishing.
- Report all commands and results.
```

Review and commit:

```bash
git add .
git commit -m "feat: establish VLC remote project foundation"
```

---

# 20. Phase 2 Codex prompt — VLC backend integration

```text
Read AGENTS.md, SPEC.md and docs/VLC_COMPATIBILITY.md.

Implement Phase 2: the typed VLC backend adapter and normalized API.

Implement:

- Backend configuration.
- VlcClientProtocol.
- Production HTTPX VLC client.
- FakeVlcClient for tests.
- VLC response parser.
- Normalized playback models.
- Capability model.
- Authentication dependency.
- Standard API errors.
- Health and status endpoints.
- Play, pause, toggle, stop, seek, volume, mute and rate endpoints.
- Playlist and track endpoints only where compatibility evidence supports them.
- Fixture-based backend tests.

Security requirements:

- No browser-provided VLC command strings.
- No arbitrary URLs.
- No shell or AppleScript execution.
- No secrets in responses or logs.
- Constant-time bearer-token comparison.
- Strict numerical validation.
- Short VLC request timeouts.
- Proper distinction between VLC authentication failure and VLC unavailability.

Use mocked VLC responses for automated tests.

If a real VLC instance is available, run the non-destructive compatibility
checks. Record actual verification honestly.

Run all backend format, lint, type and test commands before finishing.
```

Review and commit:

```bash
git add .
git commit -m "feat: implement authenticated VLC control API"
```

---

# 21. Phase 3 Codex prompt — mobile remote interface

```text
Read AGENTS.md and SPEC.md.

Implement Phase 3: the complete mobile-first remote-control frontend.

Implement:

- API client with bearer authentication.
- URL-fragment token extraction.
- Immediate removal of token from the visible URL.
- Securely scoped local token storage.
- Forget-pairing action.
- Status polling with visibility awareness and exponential backoff.
- Connection-state banner.
- Media title and time display.
- Play/pause control.
- ±10-second and ±30-second seek controls.
- Timeline with drag preview and seek-on-release.
- Volume slider and mute.
- Playback-speed selector.
- Subtitle and audio selectors based on backend capabilities.
- Playlist navigation where supported.
- Responsive mobile styling.
- Accessible labels, focus states and disabled states.
- Unit tests.

Do not send seek requests continuously while the slider is moving.

Do not hide connection errors.

Use mocked API data for frontend tests.

Run linting, type checking, unit tests and production build.
```

Review and commit:

```bash
git add .
git commit -m "feat: add mobile VLC remote interface"
```

---

# 22. Phase 4 Codex prompt — pairing and PWA

```text
Read AGENTS.md and SPEC.md.

Implement Phase 4: pairing, startup experience and PWA support.

Implement:

- Secure token generation and persistence.
- User-config-directory storage with restrictive file permissions.
- Pairing URL generation using a URL fragment.
- Terminal QR-code display.
- Local hostname and IP discovery.
- make bootstrap.
- make run.
- Production static-file serving from FastAPI.
- Web app manifest.
- Icons or clearly documented generated placeholders.
- Service worker and cached application shell.
- Safe update strategy.
- Offline and backend-unavailable states.
- Optional mDNS advertisement only if it remains reliable and well tested.
- Tests for token generation, token extraction and pairing behaviour.

Never put the token in server-side query parameters or logs.

Do not cache API command responses.

Run all project checks and verify the production build locally.
```

Review and commit:

```bash
git add .
git commit -m "feat: add secure pairing and PWA installation"
```

---

# 23. Phase 5 Codex prompt — end-to-end tests and documentation

```text
Read all repository instructions and documentation.

Implement Phase 5: complete testing and documentation.

Add:

- Playwright mobile end-to-end tests with a mocked backend.
- Connection-loss and recovery tests.
- Authentication rejection test.
- Timeline interaction test.
- Pairing and forgetting test.
- docs/ARCHITECTURE.md.
- docs/SECURITY.md.
- docs/TESTING.md.
- docs/TROUBLESHOOTING.md.
- docs/MANUAL_TEST_CHECKLIST.md.
- Complete README.md.
- VLC setup instructions appropriate for macOS.
- Clear distinction between automated and manual verification.

Run every format, lint, type-check, test and build command.

Do not claim real hardware or VLC verification unless it occurred.
```

Review and commit:

```bash
git add .
git commit -m "test: add end-to-end coverage and complete documentation"
```

---

# 24. Phase 6 Codex prompt — optional macOS LaunchAgent

```text
Read AGENTS.md and SPEC.md.

Implement the optional macOS LaunchAgent integration.

Requirements:

- Install only after explicit user action.
- Run as the current user, never root.
- Use repository-independent resolved paths.
- Provide install, status and uninstall commands.
- Document log locations.
- Do not embed secrets directly in a world-readable plist.
- Do not silently modify VLC.
- Add script-level tests where practical.
- Update README and troubleshooting documentation.

Treat this as optional. Do not destabilise the normal make run workflow.
```

Commit separately:

```bash
git add .
git commit -m "feat: add optional macOS background service"
```

---

# 25. Final Codex review prompt

```text
Perform a final repository-wide review.

Use parallel review roles if available:

1. Security reviewer:
   Focus on authentication bypass, secret leakage, arbitrary command execution,
   unsafe network exposure, URL handling, logging and PWA caching.

2. Backend reviewer:
   Focus on async correctness, HTTPX lifecycle, VLC response parsing, request
   validation, errors, timeouts and test quality.

3. Frontend reviewer:
   Focus on polling races, stale state, slider behaviour, accessibility,
   responsive mobile layout, authentication storage and error recovery.

4. Maintainability reviewer:
   Focus on architecture boundaries, duplicated logic, documentation accuracy,
   setup reliability and unnecessary complexity.

Wait for all reviews.

Then:

- Consolidate findings by severity.
- Fix all critical and high-severity issues.
- Add regression tests for each fixed defect.
- Run every repository check.
- Inspect the final Git diff.
- Report exact commands and results.
- List remaining low-severity limitations.
- Do not state that manual VLC tests passed unless they were performed.
```

Final commit:

```bash
git add .
git commit -m "fix: resolve final VLC remote review findings"
```

---

# 26. Suggested future versions

These must not delay Version 1.

## Version 1.1

- Improved subtitle and audio-track support.
- Fullscreen support after compatibility verification.
- Custom seek intervals.
- Landscape layout.
- Better playlist display.
- Keep-screen-awake support where browsers allow it.
- Haptic feedback where available.

## Version 1.2

- Tailscale-based remote access.
- HTTPS-aware setup.
- Multiple paired devices.
- Device revocation.
- Per-device access tokens.
- Token expiry and rotation.

## Version 2

- Native SwiftUI iPhone application.
- Native media controls.
- Apple Watch companion.
- Siri Shortcuts.
- General Mac media control through a tightly restricted command layer.

Version 2 must still prohibit arbitrary remote shell execution.
