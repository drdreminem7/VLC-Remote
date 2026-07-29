# Manual test checklist

Run these steps with disposable, user-controlled media. Do not mark a command
as verified unless it completed on the real Mac and VLC instance.

## Setup and pairing

- [x] Phone loaded the local UI over home Wi-Fi on 2026-07-29.
- [x] VLC 3.0.23 returned an authenticated, read-only status response through
  the temporary loopback HTTP override on 2026-07-29.
- [ ] Quit normal VLC and start it with `make vlc-http`.
- [ ] Run `make run` and scan the freshly generated QR code.
- [ ] Confirm the phone title, connection banner, and time match VLC.
- [ ] Install the app from the phone browser and reload it from the home screen.

## Playback commands

- [ ] Play and pause.
- [ ] Seek ±10 seconds.
- [ ] Drag the timeline and confirm a single final seek.
- [ ] Change volume, mute, and restore volume.
- [ ] Change playback rate.
- [ ] Stop playback.

## Recovery

- [ ] Turn Wi-Fi off on the phone and confirm the offline message.
- [ ] Restore Wi-Fi and confirm automatic recovery.
- [ ] Quit VLC and confirm the specific VLC-unavailable message.
- [ ] Restart VLC with `make vlc-http` and confirm recovery.
- [ ] Use **Forget this Mac**, then scan a new QR to pair again.

## Capability-gated controls

- [ ] Verify unsupported playlist, track, and fullscreen controls remain hidden.
- [ ] Test an advanced control only after live compatibility evidence is added.
