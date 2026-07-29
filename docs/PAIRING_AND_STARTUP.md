# Pairing and startup

The remote has two separate local services: VLC's HTTP interface stays on the
Mac at `127.0.0.1:8080`; FastAPI serves the phone UI and API on the home
network. The phone never talks to VLC directly.

## First live start

1. Quit any normally launched VLC instance.
2. From this repository, run `make vlc-http`.
3. Run `make run` in another terminal.
4. Scan the displayed QR code from a phone on the same home network.

`make vlc-http` launches VLC with a process-only override that was verified on
this Mac:

```text
--extraintf=http --http-host=127.0.0.1 --http-port=8080
```

It deliberately does not enable VLC's saved **Web** or **Lua interpreter**
preferences, because that configuration made VLC 3.0.23 exit at launch.

## Dock app start

Run `make app` to build, install, and open the optional native Mac app in
`~/Applications`. It asks for the project folder once. Each time the app is
opened from the Dock, it performs the same safe VLC launch and starts the phone
service, then displays its native QR window when ready. It does not install a
Login Item or LaunchAgent, and it never starts by itself at macOS login.

Closing the QR window leaves the remote and VLC running. **Quit Mac VLC Remote**
stops FastAPI while leaving VLC playing. The app keeps its start/build diagnostics
in `~/Library/Logs/MacVlcRemote/menu-bar-service.log` with mode `0600`; it does
not log the pairing link or either secret.

## Pairing secret handling

The first pairing operation creates a bearer token at:

```text
~/Library/Application Support/MacVlcRemote/access-token
```

The directory is mode `0700` and the token file is mode `0600`. The token is
embedded only in the QR URL fragment. The browser removes that fragment before
it makes API requests, then keeps the token only in that origin's local storage.
Use **Forget this Mac** in the UI to clear that browser copy.

The launch helper creates a separate mode-`0600` VLC password in the same
directory. It is used only by VLC and the backend; it is never sent to the
phone.

Do not share, screenshot, or paste pairing URLs into messages. To show the QR
again, run `make pairing` from the Mac.

## Installable web app

After the phone loads the remote once, use the browser's **Add to Home Screen**
or install action. The service worker caches only the application shell and
static assets. It deliberately never caches `/api/` traffic, including playback
commands and status responses.

If the UI is out of date, close it and reopen it; the service worker takes over
on the next load. Removing the installed web app clears its shell cache but does
not revoke the Mac's token. Use **Forget this Mac** first when handing a phone
to someone else.
