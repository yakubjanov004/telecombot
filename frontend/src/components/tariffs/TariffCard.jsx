import { formatPrice } from '../../utils/format';
import Button from '../ui/Button';

const BENEFITS = {
  internet: ['Cheksiz trafik', 'Barqaror tezlik', 'Wi-Fi router'],
  mobile: ['4G/5G tarmoq', 'O\'zbekiston bo\'ylab', 'Qulay narx'],
};

export default function TariffCard({ tariff, selected, onSelect, onDetails }) {
  const isInternet = tariff.service_type === 'internet';
  const benefits = BENEFITS[tariff.service_type] || [];

  return (
    <article
      className={`tariff-card ${selected ? 'tariff-card--selected' : ''}`}
      onClick={() => onSelect?.(tariff)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && onSelect?.(tariff)}
      aria-pressed={selected}
    >
      {selected && <div className="tariff-card__badge">Tanlangan</div>}

      <div className="tariff-card__type">
        {isInternet ? 'Internet' : 'Mobil'}
      </div>

      <h3 className="tariff-card__name">{tariff.name}</h3>

      <div className="tariff-card__price">
        {formatPrice(tariff.price)}
      </div>

      <ul className="tariff-card__specs">
        {isInternet ? (
          <>
            <li><span>Tezlik</span><strong>{tariff.speed || '50 Mbps'}</strong></li>
            <li><span>Trafik</span><strong>Cheksiz</strong></li>
          </>
        ) : (
          <>
            <li><span>Internet</span><strong>{tariff.mb || '—'}</strong></li>
            <li><span>Daqiqalar</span><strong>{tariff.minutes || '—'}</strong></li>
            <li><span>SMS</span><strong>{tariff.sms || '—'}</strong></li>
          </>
        )}
      </ul>

      {tariff.description && (
        <p className="tariff-card__desc">{tariff.description}</p>
      )}

      <ul className="tariff-card__benefits">
        {benefits.map((b) => (
          <li key={b}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path d="M20 6L9 17l-5-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            {b}
          </li>
        ))}
      </ul>

      <div className="tariff-card__actions" onClick={(e) => e.stopPropagation()}>
        <Button
          variant={selected ? 'primary' : 'outline'}
          size="sm"
          onClick={() => onSelect?.(tariff)}
        >
          {selected ? 'Tanlangan ✓' : 'Tanlash'}
        </Button>
        {onDetails && (
          <Button variant="ghost" size="sm" onClick={() => onDetails(tariff)}>
            Batafsil
          </Button>
        )}
      </div>
    </article>
  );
}
