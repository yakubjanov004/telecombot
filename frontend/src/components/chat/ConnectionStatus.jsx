const LABELS = {
  connecting: { text: 'Ulanmoqda...', color: 'warning' },
  connected: { text: 'Ulangan', color: 'success' },
  reconnecting: { text: 'Qayta ulanmoqda', color: 'warning' },
  failed: { text: 'Ulanib bo\'lmadi', color: 'error' },
  error: { text: 'Xatolik', color: 'error' },
  expired: { text: 'Sessiya tugadi', color: 'muted' },
};

export default function ConnectionStatus({ state, operatorOnline }) {
  const info = LABELS[state] || LABELS.connecting;

  return (
    <div className="connection-status">
      <span className={`connection-status__dot connection-status__dot--${info.color}`} aria-hidden="true" />
      <span className="connection-status__text">{info.text}</span>
      {operatorOnline && state === 'connected' && (
        <span className="connection-status__operator">Operator online</span>
      )}
    </div>
  );
}
