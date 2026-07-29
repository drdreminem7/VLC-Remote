# Mac VLC Remote

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
> Phase 2 provides the tested, authenticated VLC adapter and normalized API.
> The interface previews the new tactile remote surface; live frontend polling,
> pairing, and PWA installation arrive in the following phases.

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
make dev
```

Open `http://127.0.0.1:5173` for the Vite development UI. Its `/api` requests
are proxied to FastAPI at `http://127.0.0.1:8000`, so development does not need
permissive CORS.

Run the production-style same-origin build with:

```bash
make run
```

This builds the frontend into FastAPI's static directory and serves the UI and
API together at `http://127.0.0.1:8000`.

## Phase 2 API

`GET /api/v1/health` remains public and contains no secrets. Every status or
control endpoint requires:

```text
Authorization: Bearer <VLC_REMOTE_ACCESS_TOKEN>
```

Set a random access token containing at least 32 characters before testing the
protected API. An empty token safely rejects every protected request; persistent
token generation and QR pairing are reserved for Phase 4.

The exposed control surface is intentionally fixed:

- normalized status;
- play, pause, toggle, and stop;
- relative or absolute seek;
- volume, deterministic mute fallback, and playback rate.

No browser-provided VLC commands or URLs are accepted. Playlist, track, and
fullscreen routes are absent because the installed VLC build has no successful
live compatibility evidence for them.

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

## Security status

- The browser never receives the VLC HTTP password.
- Protected API routes use constant-time bearer-token comparison.
- The VLC URL is restricted to HTTP loopback addresses.
- Production does not configure wildcard CORS.
- No browser-controlled VLC command strings, arbitrary URLs, shell execution,
  or AppleScript exist.
- Automatic token persistence and QR pairing are intentionally deferred to
  Phase 4; do not expose an unpaired build beyond a trusted development machine.
- The intended Version 1 threat model is a trusted home/private network. Plain
  local HTTP does not protect against a malicious network administrator.

Do not commit `.env`, passwords, bearer tokens, or generated user
configuration. `.env.example` contains placeholders only.

## Testing and compatibility

Automated tests do not require VLC. Live VLC HTTP behavior remains pending
until a safe configuration can keep this VLC build open with a localhost-only
listener and user-controlled media is loaded.

- [Implementation specification](SPEC.md)
- [VLC compatibility evidence](docs/VLC_COMPATIBILITY.md)
- [Implementation checklist](docs/IMPLEMENTATION_CHECKLIST.md)

## License

[MIT](LICENSE)
