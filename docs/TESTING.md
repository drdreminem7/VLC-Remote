# Testing

Run the complete automated suite:

```bash
make format
make lint
make typecheck
make test
make e2e
make build
```

## Automated coverage

- Backend unit tests use `FakeVlcClient` and mocked HTTPX responses. They never
  require a running VLC instance.
- Frontend unit tests cover pairing fragments, secure local token handling,
  polling states, commands, slider behavior, and recovery messages.
- Playwright uses an iPhone 13 viewport and intercepted API responses. It
  covers fragment pairing/forgetting, authentication rejection, temporary loss
  and recovery, and exactly one seek request after a timeline release.

The first Playwright run may need:

```bash
npx playwright install chromium
```

This downloads a test browser only; it does not contact VLC or modify its
preferences.

## Manual coverage

See [MANUAL_TEST_CHECKLIST.md](MANUAL_TEST_CHECKLIST.md) for steps that require
the actual Mac, phone, and user-controlled media. Keep automated, local
production, and real-VLC results separate in reports.
