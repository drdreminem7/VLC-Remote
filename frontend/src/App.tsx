function StatusMark() {
  return (
    <svg aria-hidden="true" className="status-mark" viewBox="0 0 24 24">
      <circle cx="12" cy="12" r="8" />
      <circle className="status-mark__core" cx="12" cy="12" r="3" />
    </svg>
  );
}

function RewindIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <path d="M11 6 4 12l7 6V6Zm8 0-7 6 7 6V6Z" />
    </svg>
  );
}

function PlayIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <path d="m8 5 11 7-11 7V5Z" />
    </svg>
  );
}

function ForwardIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <path d="m13 6 7 6-7 6V6ZM5 6l7 6-7 6V6Z" />
    </svg>
  );
}

export default function App() {
  return (
    <main className="remote-shell">
      <header className="masthead">
        <a className="wordmark" href="/" aria-label="Mac VLC Remote home">
          <span className="wordmark__aperture" aria-hidden="true">
            VLC
          </span>
          <span>Mac Remote</span>
        </a>
        <span className="phase-label">Local / Mac</span>
      </header>

      <section className="connection-strip" aria-live="polite">
        <div className="connection-strip__state">
          <StatusMark />
          <span>Remote service ready</span>
        </div>
        <span className="connection-strip__detail">
          VLC connection not configured
        </span>
      </section>

      <section className="now-playing" aria-labelledby="media-title">
        <p className="eyebrow">No media loaded</p>
        <h1 id="media-title">Your Mac, within reach.</h1>
        <p className="now-playing__description">
          The secure local service is running. Playback controls will wake when
          the authenticated VLC connection is ready.
        </p>

        <div
          className="timeline-preview"
          role="group"
          aria-label="Inactive playback timeline"
        >
          <div className="timeline-preview__track" aria-hidden="true">
            <span />
          </div>
          <div className="timeline-preview__time">
            <time>00:00</time>
            <span>Waiting for VLC</span>
            <time>--:--</time>
          </div>
        </div>
      </section>

      <section className="transport" aria-label="Playback controls preview">
        <button
          className="transport__secondary"
          type="button"
          disabled
          aria-label="Skip backward 10 seconds — unavailable"
        >
          <RewindIcon />
          <span>10</span>
        </button>
        <button
          className="transport__primary"
          type="button"
          disabled
          aria-label="Play — unavailable"
        >
          <PlayIcon />
        </button>
        <button
          className="transport__secondary"
          type="button"
          disabled
          aria-label="Skip forward 10 seconds — unavailable"
        >
          <ForwardIcon />
          <span>10</span>
        </button>
      </section>

      <footer className="foundation-note">
        <span>Same-origin UI + API</span>
        <span aria-hidden="true">•</span>
        <span>Secrets stay on this Mac</span>
      </footer>
    </main>
  );
}
