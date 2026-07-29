# Troubleshooting

## Phone shows 400 Invalid host header

Stop `make run` with `Ctrl+C`, pull the latest code, and run `make run` again.
Pairing hostnames are normalized to lowercase for browser host headers. Prefer
the freshly printed private IP URL if `.local` resolution is unreliable.

## Phone shows “Pair this phone” or 401

The phone token is missing, stale, or was forgotten. Run `make pairing` on the
Mac and scan the new QR. If a pairing URL was exposed, rotate the Mac token
before pairing again.

## Backend reachable but VLC unavailable

Quit normal VLC, run `make vlc-http`, then restart `make run`. Do not enable
VLC's saved Web or Lua interpreter settings on this VLC 3.0.23 installation.

## VLC exits immediately after enabling Web

Launch the recovery instance with:

```bash
open -na /Applications/VLC.app --args --extraintf=
```

In VLC's advanced preferences, turn off Web and Lua interpreter, clear Extra
interface modules, save, quit, and relaunch normally. Use `make vlc-http` for
remote control instead.

## Phone cannot reach the Mac

Confirm both devices are on the same private Wi-Fi, disable any VPN that blocks
local LAN traffic, and try the printed private IP rather than the `.local` name.
Never open port 8000 to the public internet.

## Mac app does not start

Install it with `make app`, then choose the project folder that contains the
repository `Makefile` and `.venv` directory. If it reports that VLC is already
running, quit VLC and reopen the app: the launcher deliberately refuses to
change a normal VLC instance's saved settings. The service log is at
`~/Library/Logs/MacVlcRemote/menu-bar-service.log`; it contains start/build
diagnostics but not pairing links or passwords.

## UI does not update after deployment

Close and reopen the web app. The service worker updates the static shell on
the next load and never caches API data.
