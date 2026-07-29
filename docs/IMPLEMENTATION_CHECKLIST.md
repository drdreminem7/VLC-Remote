# Implementation checklist

This checklist follows the gated phases in `SPEC.md`. A phase should not be
marked complete until its checks pass and its manual verification claims are
accurate.

## Phase 0 — environment and compatibility

- [x] Inspect the starting repository.
- [x] Record Python, Node.js, npm, Git, macOS, and VLC versions.
- [x] Inspect installed VLC HTTP interface files and safe CLI help.
- [x] Probe the default status endpoint without changing VLC state.
- [x] Add `scripts/check_vlc.py`.
- [x] Add `docs/VLC_COMPATIBILITY.md`.
- [x] Record incompatibilities, unknowns, and required capability gates.
- [x] Reproduce and document the VLC 3.0.23 Web/Lua launch incompatibility,
  then restore normal VLC startup.
- [ ] Run a live authenticated status check after the VLC HTTP interface is
  safely configured without breaking normal startup.
- [ ] Run state-changing compatibility checks with user-controlled media and
  explicit consent.
- [ ] Review and promote redacted responses into test fixtures.

## Phase 1 — repository foundation

- [x] Add Python project configuration and backend package skeleton.
- [x] Add the Vite React TypeScript frontend.
- [x] Add Makefile, ignore rules, environment example, and README.
- [x] Implement the public health route without exposing secrets.
- [x] Add the accessible mobile application shell.
- [x] Establish backend and frontend test infrastructure.
- [x] Add continuous integration.
- [x] Make all required `make` commands exist.
- [x] Run formatting, linting, type checks, tests, and production builds.

## Phase 2 — authenticated VLC backend

- [x] Implement validated settings and secret handling.
- [x] Define the typed VLC protocol, HTTPX client, parser, and fake client.
- [x] Add normalized status and capability models.
- [x] Add constant-time bearer-token authentication.
- [x] Add standard safe API errors.
- [x] Add health, status, playback, seek, audio, mute, and rate routes.
- [x] Gate playlist, track, and fullscreen operations on compatibility evidence.
- [x] Deduplicate or briefly cache concurrent status requests.
- [x] Add fixture-driven parser, adapter, auth, validation, and API tests.
- [x] Run backend formatting, linting, mypy, and tests.

## Phase 3 — mobile remote

- [ ] Add the authenticated API client.
- [ ] Extract pairing tokens from URL fragments and immediately clean the URL.
- [ ] Add local pairing storage and “Forget this Mac”.
- [ ] Add visibility-aware, abortable polling with failure backoff.
- [ ] Render all required connection states and recovery guidance.
- [ ] Add media, playback, seek, volume, mute, and speed controls.
- [ ] Add seek preview with one command on release.
- [ ] Gate track and playlist controls on backend capabilities.
- [ ] Meet mobile touch, safe-area, keyboard, and accessibility requirements.
- [ ] Add frontend unit tests and run all frontend checks.

## Phase 4 — pairing, startup, and PWA

- [ ] Generate and persist at least 32 random bytes for the access token.
- [ ] Restrict token-file permissions to the current user.
- [ ] Generate fragment-based pairing URLs and terminal QR codes.
- [ ] Add local hostname/IP discovery.
- [ ] Implement `make bootstrap` and `make run`.
- [ ] Serve the production frontend and API from FastAPI on one origin.
- [ ] Add manifest, icons, service worker, and safe cache versioning.
- [ ] Ensure service workers never cache API command responses.
- [ ] Verify production startup and pairing behaviour locally.

## Phase 5 — end-to-end coverage and documentation

- [ ] Add mocked-backend Playwright tests at an iPhone-like viewport.
- [ ] Cover pairing, commands, timeline, auth failure, loss, and recovery.
- [ ] Complete architecture, setup, security, testing, troubleshooting, and
  manual-check documentation.
- [ ] Complete the README.
- [ ] Run every repository check and production build.
- [ ] Clearly separate automated, local-browser, and real-VLC verification.

## Phase 6 — optional LaunchAgent

- [ ] Decide whether the optional integration is justified.
- [ ] Add explicit current-user install, status, and uninstall operations.
- [ ] Resolve paths without developer-specific hard-coding.
- [ ] Keep secrets out of world-readable plist content.
- [ ] Document logs and recovery without changing VLC preferences.

## Final review

- [ ] Review security boundaries and add regressions for serious findings.
- [ ] Review async backend lifecycle and parser failure behaviour.
- [ ] Review polling races, slider behaviour, accessibility, and PWA caching.
- [ ] Review maintainability, documentation accuracy, and setup reliability.
- [ ] Fix every critical and high-severity issue.
- [ ] Run format, lint, type checks, unit tests, E2E tests, and builds.
- [ ] Inspect the final diff and list remaining low-severity limitations.
- [ ] Complete the real-VLC manual checklist without inventing results.
