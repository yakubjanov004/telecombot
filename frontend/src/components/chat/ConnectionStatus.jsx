const LABELS = {
  connecting: { text: 'Chatga ulanmoqda...', color: 'warning' },
  connected: { text: 'Chat ochiq', color: 'success' },
  reconnecting: { text: 'Qayta ulanmoqda...', color: 'warning' },
  failed: { text: 'Ulanish amalga oshmadi', color: 'error' },
  error: { text: 'Ulanishda xatolik', color: 'error' },
  expired: { text: 'Chat tugagan', color: 'muted' },
};

export default function ConnectionStatus({ state, operatorOnline }) {
  const info = LABELS[state] || LABELS.connecting;

  return (
    <div className="connection-status">
      <span className={`connection-status__dot connection-status__dot--${info.color}`} aria-hidden="true" />
      <span className="connection-status__text">{info.text}</span>
      {operatorOnline && state === 'connected' && (
        <span className="connection-status__operator">Operator ulandi</span>
      )}
    </div>
  );
}
