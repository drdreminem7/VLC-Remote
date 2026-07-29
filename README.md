# VLC Remote

A secure, local, mobile-first web remote for VLC Media Player on macOS. The
React interface runs in a phone browser; a FastAPI service on the Mac is the
only component allowed to communicate with VLC's localhost HTTP interface.

```text
Phone browser / installed PWA
              |
              | same-origin local HTTP
              v
       FastAPI on the Mac
              |
              | HTTP Basic auth on localhost
              v
       VLC HTTP interface
```

> [!NOTE]
> Phase 4 provides secure local pairing, terminal QR output, and an installable
> PWA shell. The live VLC launch method is verified for read-only status; media
> commands still require user-controlled compatibility testing.

## Requirements

- macOS with VLC 3.x
- Python 3.11 or newer
- Node.js 22 or newer
- npm 10 or newer

The inspected development Mac currently has VLC 3.0.23, Python 3.12.10,
Node.js 22.14.0, and npm 10.9.2.

## Quick start

```bash
make bootstrap
make vlc-http
make run
```

Before `make vlc-http`, quit any normally launched VLC instance. This explicit
helper starts a new VLC process with the proven loopback-only HTTP override; it
does not modify the broken Web/Lua preference. `make run` displays the pairing
QR code. Scan it from a phone on the same home network.

For frontend development without live VLC, use `make dev` and open
`http://127.0.0.1:5173`. Its `/api` requests are proxied to FastAPI at
`http://127.0.0.1:8000`, so development does not need permissive CORS.

Run the production-style same-origin build with:

```bash
make run
```

This builds the frontend into FastAPI's static directory and serves the UI and
API together at `http://127.0.0.1:8000`.

## Mac application launcher

Build, install, and open the native Mac app with its dedicated remote icon:

```bash
make app
```

The app is installed at `/Applications/VLC Remote.app` and appears in the
Dock. On its first launch, choose this project folder. Every later app launch
automatically starts the safe loopback-only VLC helper, builds and starts the
phone service, then shows the native pairing QR as soon as the service is ready.
There is no Login Item, LaunchAgent, or automatic start at macOS login.

Close the QR window whenever you like; the phone remote keeps running. Choose
**Quit VLC Remote** from the Dock to stop the phone service while leaving
VLC itself open. If the project is moved later, choose its new folder from the
app menu.

## Phase 2 API

`GET /api/v1/health` remains public and contains no secrets. Every status or
control endpoint requires:

```text
Authorization: Bearer <VLC_REMOTE_ACCESS_TOKEN>
```

An empty `VLC_REMOTE_ACCESS_TOKEN` causes a 32-byte token to be generated in
the current user's protected Application Support directory when pairing or a
protected endpoint is first used. Do not set a weaker token manually.

The exposed control surface is intentionally fixed:

- normalized status;
- play, pause, toggle, and stop;
- relative or absolute seek;
- volume, deterministic mute fallback, and playback rate.

No browser-provided VLC commands or URLs are accepted. Playlist, track, and
fullscreen routes are absent because the installed VLC build has no successful
live compatibility evidence for them.

## Mobile remote

The phone UI polls a paired Mac every 900 ms while visible and every 6 seconds
while hidden. It aborts obsolete requests, stops sending commands while the
phone is offline, and uses capped exponential retry delays when the service is
unavailable. Its connection banner distinguishes an unpaired phone, offline
phone, unavailable VLC, and unreachable Mac.

Pairing URLs use a token in the fragment, for example
`http://mac.local:8000/#token=<token>`. The UI validates and stores a valid
token for this origin, then immediately removes the fragment with
`history.replaceState` so it is not left in the visible address bar. `make run`
prints a terminal QR code and `make pairing` shows it again without restarting
the service. Do not hand-author, share, or screenshot a pairing URL.

Use the settings button to select **Forget this Mac** and remove the token from
this browser. The UI always renders only the controls advertised by the backend
capability flags, so unsupported playlist and track controls remain absent.

## VLC HTTP interface status

Do **not** enable **Web** or **Lua interpreter** in the installed VLC 3.0.23
build. On this Mac, enabling the Web interface saved `extraintf=lua:http` and
caused later normal VLC launches to exit immediately. Disabling Web alone left
`extraintf=lua`; the advanced **Extra interface modules** field also had to be
cleared before VLC opened normally again.

Live VLC HTTP integration is therefore blocked on a safe, reproducible launch
configuration. See [VLC compatibility](docs/VLC_COMPATIBILITY.md) for the
observed evidence and recovery steps. The application foundation and mocked
backend work do not require the live interface.

When a safe setup is established, confirm that VLC is listening only on
localhost before sending credentials:

```bash
lsof -nP -iTCP:8080 -sTCP:LISTEN
```

Proceed only when the listener is shown as `127.0.0.1:8080`. If it is shown as
`*:8080` or another network-facing address, disable the Web interface until the
host restriction is corrected.

Then run the safe status diagnostic without putting the password in a file:

```bash
read -s VLC_HTTP_PASSWORD
export VLC_HTTP_PASSWORD
VLC_HTTP_BASE_URL=http://127.0.0.1:8080 python3 scripts/check_vlc.py
unset VLC_HTTP_PASSWORD
```

Do not run the diagnostic on this VLC installation yet. Once a safe listener
exists, its default mode sends no playback commands and never prints the
password. See [VLC compatibility](docs/VLC_COMPATIBILITY.md) before running its
explicit state-changing mode.

## Project commands

| Command | Purpose |
| --- | --- |
| `make bootstrap` | Create `.venv` and install Python and npm dependencies |
| `make dev` | Run FastAPI and Vite development servers |
| `make build` | Build the frontend into FastAPI's static directory |
| `make format` | Format Python source |
| `make lint` | Check Python and frontend lint/format rules |
| `make typecheck` | Run mypy and TypeScript checks |
| `make test` | Run backend and frontend unit tests |
| `make run` | Build and run the same-origin production-style service |
| `make menu-bar-build` | Build the native macOS application bundle |
| `make menu-bar` | Build and open the application from the project folder |
| `make app` | Install and open the auto-starting Dock application |

## Security status

- The browser never receives the VLC HTTP password.
- Protected API routes use constant-time bearer-token comparison.
- The VLC URL is restricted to HTTP loopback addresses.
- Production does not configure wildcard CORS.
- No browser-controlled VLC command strings, arbitrary URLs, shell execution,
  or AppleScript exist.
- A valid pairing token is kept only in this origin's browser local storage and
  is removed on “Forget this Mac”; the fragment is cleared before the UI polls.
- The generated token lives in `~/Library/Application Support/MacVlcRemote`
  with directory mode `0700` and file mode `0600`.
- The intended Version 1 threat model is a trusted home/private network. Plain
  local HTTP does not protect against a malicious network administrator.

Do not commit `.env`, passwords, bearer tokens, or generated user
configuration. `.env.example` contains placeholders only.

## Testing and compatibility

Automated tests do not require VLC. Live VLC HTTP behavior remains pending
until user-controlled media is loaded for state-changing checks. The safe
loopback status path is verified; playback commands remain manual work.

Run the automated checks with:

```bash
make format
make lint
make typecheck
make test
make e2e
make build
```

The E2E suite uses a mocked backend at an iPhone-like viewport. It does not
claim real VLC playback behavior. See the manual checklist before relying on
any live control beyond the verified status path.

- [Implementation specification](SPEC.md)
- [VLC compatibility evidence](docs/VLC_COMPATIBILITY.md)
- [Pairing and startup](docs/PAIRING_AND_STARTUP.md)
- [VLC setup](docs/VLC_SETUP.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Security](docs/SECURITY.md)
- [Testing](docs/TESTING.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)
- [Manual test checklist](docs/MANUAL_TEST_CHECKLIST.md)
- [Implementation checklist](docs/IMPLEMENTATION_CHECKLIST.md)

## License

[MIT](LICENSE)
