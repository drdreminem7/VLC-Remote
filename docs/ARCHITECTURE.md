# Architecture

Mac VLC Remote is a same-origin local web application. The phone never contacts
VLC directly and never receives VLC's password.

```text
Phone browser / PWA
        │  HTTP on trusted home Wi-Fi
        ▼
FastAPI + static React app on the Mac :8000
        │  HTTP Basic authentication on loopback only
        ▼
VLC HTTP interface on 127.0.0.1:8080
```

## Components

- `frontend/` is the React remote. It keeps the pairing token in browser local
  storage, sends it only as a bearer header, and removes it from a pairing URL
  fragment before polling.
- `backend/app/routers/` exposes a fixed, typed API. It accepts no arbitrary
  VLC command, URL, shell command, or AppleScript input.
- `backend/app/services/vlc_client.py` is the only VLC protocol adapter.
  Parsing, Basic authentication, timeouts, and error translation stay there.
- `backend/app/services/secret_store.py` owns current-user secret files.
- `scripts/launch_vlc_http.py` explicitly starts VLC with the verified
  loopback-only HTTP override; it does not change VLC preferences.
- `macos/MenuBarLauncher.swift` is an optional native, on-demand controller. It
  runs only fixed local scripts from a user-selected project folder, writes
  service output to a private user log, and renders the pairing QR locally.

## Runtime flow

`make run` builds the Vite app into `backend/app/static`, prints a fragment
pairing URL/QR, and runs FastAPI on one origin. The phone loads the app from the
Mac, then polls `/api/v1/status` with the stored bearer token. FastAPI maps each
fixed request to a typed VLC operation and returns normalized state.

`make menu-bar` builds an optional `Mac VLC Remote.app`. It never starts at
login. Its **Start Remote** action invokes `scripts/run_menu_bar_service.py`,
which runs the same safe VLC helper, then builds and starts FastAPI without
printing the pairing URL to a terminal or service log. The native app receives
the URL through a private child-process pipe and displays its QR in a Mac window.

## PWA behavior

The service worker caches only same-origin static UI requests. Any path
beginning `/api` bypasses the cache, as do non-GET requests. This prevents
status or command responses from being replayed offline.
