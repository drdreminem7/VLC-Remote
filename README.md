# VLC Remote

A local, mobile-first remote for VLC on macOS. Open the remote on a phone,
scan one QR code, and control VLC from the same home network.

<p align="center">
  <img src="macos/AppIcon.png" width="128" alt="VLC Remote app icon">
</p>

## What it does

- Pairs a phone to one Mac with a QR code.
- Controls play/pause, ±10-second seek, timeline seek, volume (0–200), mute,
  and playback speed.
- Selects embedded audio and subtitle tracks, and adjusts subtitle timing in
  50 ms steps.
- Shows a movie poster while media is playing, using TMDB when configured.
- Lets a paired phone choose a movie from `Desktop/Movies`, loading local
  sidecar subtitles, preserving playback position, and entering fullscreen.
- Searches OpenSubtitles from the phone, prioritizing exact file and release
  matches before downloading a subtitle beside the movie.
- Runs as an installable phone web app and an optional Mac Dock app.
- Keeps VLC's HTTP password on the Mac. The phone never receives it.

```text
Phone browser or PWA → FastAPI on the Mac → VLC HTTP on 127.0.0.1
```

## Screenshots

<p align="center">
  <img src="docs/screenshots/IMG_1348.jpg" width="31%" alt="VLC Remote playing Star Wars">
  <img src="docs/screenshots/IMG_1349.jpg" width="31%" alt="VLC Remote playing Stalker">
  <img src="docs/screenshots/IMG_1350.jpg" width="31%" alt="VLC Remote playing Chinatown">
</p>

Future real-device screenshots belong in [`docs/screenshots`](docs/screenshots).
Never include a pairing URL or token in a screenshot.

## Requirements

- macOS with VLC 3.x
- Python 3.11+
- Node.js 22+
- npm 10+

## Quick start

```bash
make bootstrap
make vlc-http
make run
```

Scan the QR code from a phone on the same private Wi-Fi. `make vlc-http` starts
VLC with a loopback-only HTTP override and does not change saved VLC
preferences. `make run` serves the React app and API together on port 8000.

To show a fresh QR without restarting the service:

```bash
make pairing
```

## Movie library

Put movies anywhere inside `~/Desktop/Movies`; each movie may live in its own
named folder. Tap the poster/touch surface to open the picker, then tap a poster
to play it. The same picker is available in
**Settings → Movie library**.

The phone receives only opaque IDs and display metadata. The Mac re-scans and
validates each selection inside `Desktop/Movies` before VLC is asked to open it.
Compatible subtitle files directly beside the selected movie (`.srt`, `.ass`,
`.vtt`, and similar formats) are added to VLC automatically.

Open **Settings → Subtitles** to select embedded VLC tracks, load a sidecar
file, or search OpenSubtitles and download a result beside the current movie.
Online search requires the three `OPENSUBTITLES_…` values in `.env`; the
account password, API key, and temporary login token stay on the Mac.

Open **Settings → Audio track** to switch between the audio streams available
inside the current movie. Hardware output—such as an HDMI TV—is selected by
macOS, so leave VLC's audio device set to **Default**.

## Mac app

Build, install, and open the Dock app:

```bash
make app
```

It installs as **VLC Remote.app** in `/Applications`. On first launch, choose
this project folder. Later launches start the local remote and display its QR
code automatically. Closing the QR window leaves the remote running; quitting
the Dock app stops the remote and asks VLC to quit normally.

### Optional one-tap iPhone launch

An iPhone Shortcut can start the Dock app over SSH, then open the pairing URL
it receives from the Mac. The installer places its restricted helper in a
private user-local command directory, so the Shortcut does not need access to
the project folder on Desktop.

Enable **System Settings → General → Sharing → Remote Login**, then configure
Shortcuts' **Run Script over SSH** action with an SSH key rather than a Mac
password. Authorize that public key with a forced command to
`vlc-remote-shortcut`; never use it as a general-purpose SSH key. Keep the
Shortcut limited to a trusted home network and do not configure router port
forwarding for SSH.

For the Shortcut's SSH **Host**, use the Mac's Bonjour name, for example
`Harrys-MacBook-Pro.local`, rather than a fixed `192.168.x.x` address. The
`.local` name works when the iPhone and Mac join another normal home Wi-Fi
network together; a numeric address changes from network to network.

## Optional movie posters

Create a local `.env` from `.env.example`, then add a TMDB API Read Access
Token and, optionally, your OpenSubtitles account and consumer API key:

```text
TMDB_API_TOKEN=your_token_here
OPENSUBTITLES_USERNAME=your_username
OPENSUBTITLES_PASSWORD=your_password
OPENSUBTITLES_API_KEY=your_consumer_api_key
```

These values stay on the Mac. They are never sent to the phone and must never
be committed.

## Development and checks

| Command | Purpose |
| --- | --- |
| `make dev` | Run the development servers |
| `make build` | Build the production frontend |
| `make format` | Format Python source |
| `make lint` | Run Python and frontend linting |
| `make typecheck` | Run Python and TypeScript checks |
| `make test` | Run unit tests |
| `make e2e` | Run iPhone-sized browser tests |
| `make menu-bar-build` | Build the native macOS app bundle |

Run the complete automated suite before a contribution:

```bash
make format
make lint
make typecheck
make test
make e2e
make build
```

## Security

- VLC listens only on `127.0.0.1`; the phone talks only to the Mac-hosted app.
- The pairing token is kept in the URL fragment, then removed before requests.
- The frontend accepts only fixed, typed control actions—never arbitrary VLC
  commands, URLs, shell commands, or AppleScript.
- Movie selections are constrained to files currently inside `Desktop/Movies`.
- This is for a trusted private network. Do not expose port 8000 to the public
  internet.
- The optional iPhone launch key is restricted to one local command; it is not
  a general SSH login.

More detail: [VLC setup](docs/VLC_SETUP.md),
[security](docs/SECURITY.md), and [troubleshooting](docs/TROUBLESHOOTING.md).

## License

[MIT](LICENSE)
