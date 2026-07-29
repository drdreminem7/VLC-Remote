# VLC setup on this Mac

The installed VLC 3.0.23 build must not use its saved Web or Lua interpreter
preferences: that configuration made normal VLC launches exit.

For remote control, use the explicit helper instead:

```bash
make vlc-http
```

It starts a new VLC process with HTTP bound only to `127.0.0.1:8080`, creates a
private VLC password if necessary, and leaves saved preferences unchanged.
Then run `make run` for the phone-facing server and QR pairing code.

Use `scripts/check_vlc.py` only for its default read-only diagnostic unless you
have user-controlled media and explicitly pass both integration-test flags.
