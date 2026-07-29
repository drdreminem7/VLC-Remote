function StatusDot() {
  return <span className="status-dot" aria-hidden="true" />;
}

function LockIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <path d="M7.75 10V7.75a4.25 4.25 0 0 1 8.5 0V10" />
      <rect x="5.25" y="10" width="13.5" height="10" rx="3" />
      <path d="M12 14.25v2.5" />
    </svg>
  );
}

function SettingsIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <circle cx="12" cy="12" r="3" />
      <path d="M19 12a7.3 7.3 0 0 0-.1-1.2l2-1.55-2-3.45-2.45 1a7 7 0 0 0-2.05-1.2L14 3h-4l-.4 2.6a7 7 0 0 0-2.05 1.2l-2.45-1-2 3.45 2 1.55A7.3 7.3 0 0 0 5 12c0 .4 0 .8.1 1.2l-2 1.55 2 3.45 2.45-1a7 7 0 0 0 2.05 1.2L10 21h4l.4-2.6a7 7 0 0 0 2.05-1.2l2.45 1 2-3.45-2-1.55c.07-.4.1-.8.1-1.2Z" />
    </svg>
  );
}

function RewindIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <path d="M11.5 7 5 12l6.5 5V7Zm7.5 0-6.5 5 6.5 5V7Z" />
    </svg>
  );
}

function ForwardIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <path d="m12.5 7 6.5 5-6.5 5V7ZM5 7l6.5 5L5 17V7Z" />
    </svg>
  );
}

function PlayIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <path d="m8.25 5.75 10 6.25-10 6.25V5.75Z" />
    </svg>
  );
}

function VolumeDownIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <path d="M5 10v4h3l4 3.5v-11L8 10H5Z" />
      <path d="M15.5 9.5a4 4 0 0 1 0 5" />
    </svg>
  );
}

function VolumeUpIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <path d="M4 10v4h3l4 3.5v-11L7 10H4Z" />
      <path d="M14 9a4.5 4.5 0 0 1 0 6M16.5 6.5a8 8 0 0 1 0 11" />
    </svg>
  );
}

function MuteIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <path d="M5 10v4h3l4 3.5v-11L8 10H5Z" />
      <path d="m16 10 4 4m0-4-4 4" />
    </svg>
  );
}

function SpeedIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <path d="M5 16a8 8 0 1 1 14 0" />
      <path d="m12 13 4-4" />
      <path d="M8 18h8" />
    </svg>
  );
}

export default function App() {
  return (
    <main className="experience">
      <section className="remote" aria-label="Mac VLC remote">
        <header className="remote-header">
          <div className="device">
            <span className="device__mark" aria-hidden="true">
              V
            </span>
            <span className="device__copy">
              <strong>Living room Mac</strong>
              <span>
                <StatusDot />
                Backend secured
              </span>
            </span>
          </div>

          <button
            className="icon-button"
            type="button"
            disabled
            aria-label="Open remote settings — available in a later phase"
          >
            <SettingsIcon />
          </button>
        </header>

        <section className="touch-surface" aria-labelledby="media-title">
          <div className="touch-surface__texture" aria-hidden="true" />
          <div className="touch-surface__content">
            <p className="eyebrow">VLC setup paused</p>
            <h1 id="media-title">Ready when VLC is.</h1>
            <p className="touch-surface__message">
              Live control stays off until VLC can run safely.
            </p>

            <span className="security-chip">
              <LockIcon />
              Local API protected
            </span>
          </div>

          <div
            className="timeline"
            role="group"
            aria-label="Playback timeline unavailable"
          >
            <div className="timeline__track" aria-hidden="true">
              <span />
            </div>
            <div className="timeline__labels">
              <time>00:00</time>
              <span>Waiting for VLC</span>
              <time>--:--</time>
            </div>
          </div>
        </section>

        <section className="transport" aria-label="Playback controls">
          <button
            className="round-button round-button--secondary"
            type="button"
            disabled
            aria-label="Skip backward 10 seconds — VLC unavailable"
          >
            <RewindIcon />
            <span>10</span>
          </button>

          <button
            className="round-button round-button--primary"
            type="button"
            disabled
            aria-label="Play — VLC unavailable"
          >
            <PlayIcon />
          </button>

          <button
            className="round-button round-button--secondary"
            type="button"
            disabled
            aria-label="Skip forward 10 seconds — VLC unavailable"
          >
            <ForwardIcon />
            <span>10</span>
          </button>
        </section>

        <section className="utility-controls" aria-label="Audio controls">
          <button
            className="utility-button"
            type="button"
            disabled
            aria-label="Mute — VLC unavailable"
          >
            <MuteIcon />
            <span>Mute</span>
          </button>

          <div className="volume-rocker" role="group" aria-label="Volume">
            <button type="button" disabled aria-label="Volume down — unavailable">
              <VolumeDownIcon />
            </button>
            <span aria-hidden="true" />
            <button type="button" disabled aria-label="Volume up — unavailable">
              <VolumeUpIcon />
            </button>
          </div>

          <button
            className="utility-button"
            type="button"
            disabled
            aria-label="Playback speed — VLC unavailable"
          >
            <SpeedIcon />
            <span>Speed</span>
          </button>
        </section>

        <footer className="remote-footer" aria-live="polite">
          <span className="remote-footer__state">
            <StatusDot />
            Phase 2 API ready
          </span>
          <span>Live VLC paused for safety</span>
        </footer>
      </section>

      <aside className="room-note" aria-label="Remote status summary">
        <p className="eyebrow">Mac VLC Remote / 02</p>
        <h2>A quieter way to stay in the film.</h2>
        <p>
          The secure control layer is ready. Live VLC access remains disabled
          while its Web interface is incompatible with this Mac.
        </p>
        <dl>
          <div>
            <dt>Control layer</dt>
            <dd>Authenticated</dd>
          </div>
          <div>
            <dt>VLC link</dt>
            <dd>Safely offline</dd>
          </div>
        </dl>
      </aside>
    </main>
  );
}
