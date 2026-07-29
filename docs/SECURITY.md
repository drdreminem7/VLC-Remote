# Security

## Boundaries

- VLC listens only on `127.0.0.1:8080` when started by `make vlc-http`.
- The phone reaches only FastAPI on the Mac's private-network address.
- The VLC HTTP password stays in a mode-`0600` current-user file and is never
  included in frontend code, responses, logs, or QR URLs.
- The remote bearer token is generated from 32 random bytes, stored in a
  mode-`0600` file beneath a mode-`0700` Application Support directory, and
  compared with `compare_digest`.

## Pairing

The QR code contains `#token=…`, not a query parameter. URL fragments are not
sent in HTTP requests. The frontend stores a valid token only for the remote's
origin, removes the fragment with `history.replaceState`, and offers **Forget
this Mac** to remove it.

Treat a pairing URL like a password. If it is exposed, stop `make run`, rotate
the token file, restart `make run`, and pair phones again. Never paste a pairing
URL into chat, screenshots, issue trackers, or logs.

## Network model

Version 1 is for a trusted home/private network. Its HTTP traffic is not
encrypted, so a hostile network administrator could observe it. Do not expose
port 8000 through router port forwarding. For remote access, use a private,
encrypted network such as Tailscale in a later version.

## Input and caching controls

- Only predefined routes and typed numerical payloads reach VLC.
- State changes are POST-only.
- VLC URLs are limited to local loopback HTTP.
- Trusted hosts reject wildcard configuration.
- Browser tokens are never put in server-side URLs.
- The PWA service worker never caches `/api` requests or command responses.
