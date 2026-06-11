import Button from '../components/ui/Button';
import Rating from '../components/ui/Rating';
import { formatDateTime } from '../utils/format';

export default function SessionCompleted({ sessionInfo, onRestart }) {
  const {
    application_type: serviceType,
    tariff,
    completed_at: completedAt,
  } = sessionInfo || {};

  const completedTime = completedAt || new Date().toISOString();

  return (
    <div className="page page--status">
      <div className="status-card status-card--completed">
        <div className="status-card__success-icon" aria-hidden="true">
          <svg width="64" height="64" viewBox="0 0 64 64" fill="none">
            <circle cx="32" cy="32" r="30" stroke="currentColor" strokeWidth="3" />
            <path d="M20 32l8 8 16-16" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>

        <h1 className="status-card__title">Sessiya yakunlandi</h1>
        <p className="status-card__subtitle">
          Operator bilan suhbat muvaffaqiyatli yakunlandi. Rahmat!
        </p>

        <dl className="session-summary">
          <div className="session-summary__row">
            <dt>Xizmat turi</dt>
            <dd>{serviceType === 'internet' ? 'Internet' : 'Mobil'}</dd>
          </div>
          {tariff && (
            <div className="session-summary__row">
              <dt>Tanlangan tarif</dt>
              <dd>{tariff.name}</dd>
            </div>
          )}
          <div className="session-summary__row">
            <dt>Yakunlangan vaqt</dt>
            <dd>{formatDateTime(completedTime)}</dd>
          </div>
        </dl>

        <Rating label="Xizmat sifatini baholang" onRate={(v) => console.log('Rating:', v)} />

        <Button variant="primary" size="lg" onClick={onRestart}>
          Yangi ariza yaratish
        </Button>
      </div>
    </div>
  );
}
