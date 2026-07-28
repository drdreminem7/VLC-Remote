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
> Phase 1 establishes the tested project foundation and application shell.
> Authenticated playback controls, pairing, and PWA installation arrive in the
> following implementation phases.

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

## Enable VLC's HTTP interface

These menu names match the installed VLC 3.0.23 build and may vary slightly:

1. Open VLC and choose **VLC media player → Settings…** (or press `⌘,`).
2. At the bottom of the settings window, change **Show settings** to **All**.
3. In the tree, open **Interface → Main interfaces** and enable **Web**.
4. Open **Interface → Main interfaces → Lua**.
5. Set a strong password in the **Lua HTTP / Password** field.
6. Search the advanced settings for **HTTP server address** and set it to
   `127.0.0.1` where the installed build exposes that field.
7. Save the settings, quit VLC completely, and reopen it.

Confirm that VLC is listening locally:

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

The default diagnostic sends no playback commands and never prints the
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
- Production does not configure wildcard CORS.
- No browser-controlled VLC commands or shell execution exist.
- Real bearer-token pairing is intentionally not implemented until Phase 2/4;
  do not expose this foundation build beyond a trusted development machine.
- The intended Version 1 threat model is a trusted home/private network. Plain
  local HTTP does not protect against a malicious network administrator.

Do not commit `.env`, passwords, bearer tokens, or generated user
configuration. `.env.example` contains placeholders only.

## Testing and compatibility

Automated tests do not require VLC. Live VLC HTTP behavior remains pending
until the interface is enabled and a user-controlled media file is loaded.

- [Implementation specification](SPEC.md)
- [VLC compatibility evidence](docs/VLC_COMPATIBILITY.md)
- [Implementation checklist](docs/IMPLEMENTATION_CHECKLIST.md)

## License

[MIT](LICENSE)
