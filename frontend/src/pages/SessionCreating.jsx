import useSessionPoll from '../hooks/useSessionPoll';

const STATE_ICONS = {
  creating: '⏳',
  topic: '🔗',
  searching: '🔍',
  connected: '✅',
};

export default function SessionCreating({ sessionId, onReady }) {
  const { currentState, progress, error } = useSessionPoll(sessionId, onReady);

  return (
    <div className="page page--status">
      <div className="status-card">
        <div className="status-card__animation">
          <div className="status-card__pulse" aria-hidden="true" />
          <span className="status-card__icon" aria-hidden="true">
            {STATE_ICONS[currentState.key] || '⏳'}
          </span>
        </div>

        <h1 className="status-card__title">{currentState.label}</h1>
        <p className="status-card__subtitle">
          Iltimos kuting, operator bilan bog&apos;lanish tayyorlanmoqda
        </p>

        <div className="status-card__progress" role="progressbar" aria-valuenow={progress} aria-valuemin={0} aria-valuemax={100}>
          <div className="status-card__progress-bar" style={{ width: `${progress}%` }} />
        </div>

        <ul className="status-card__steps">
          {[
            { key: 'creating', label: 'Sessiya yaratilmoqda' },
            { key: 'topic', label: 'Topic yaratilmoqda' },
            { key: 'searching', label: 'Operator qidirilmoqda' },
            { key: 'connected', label: 'Operatorga ulandi' },
          ].map((s) => (
            <li
              key={s.key}
              className={
                currentState.key === s.key ? 'active' :
                ['creating', 'topic', 'searching', 'connected'].indexOf(currentState.key) >
                ['creating', 'topic', 'searching', 'connected'].indexOf(s.key) ? 'done' : ''
              }
            >
              <span className="status-card__step-dot" aria-hidden="true" />
              {s.label}
            </li>
          ))}
        </ul>

        {error && <div className="alert alert--error">{error}</div>}
      </div>
    </div>
  );
}
