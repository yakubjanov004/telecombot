import { formatPrice } from '../../utils/format';

export default function TariffGroupCard({ group, onSelect }) {
  const minPrice = group.minPrice;
  const count = group.tariffs?.length || group.count || 0;

  return (
    <button
      type="button"
      className="tariff-group-card"
      onClick={() => onSelect?.(group)}
    >
      <div className="tariff-group-card__icon" aria-hidden="true">
        {group.icon}
      </div>
      <div className="tariff-group-card__body">
        <h3 className="tariff-group-card__title">{group.title}</h3>
        <p className="tariff-group-card__desc">{group.description}</p>
        <div className="tariff-group-card__meta">
          <span>{count} ta tarif</span>
          {minPrice != null && (
            <span className="tariff-group-card__price">
              {minPrice === 0 ? 'Bepul' : `${formatPrice(minPrice)} dan`}
            </span>
          )}
        </div>
      </div>
      <span className="tariff-group-card__arrow" aria-hidden="true">→</span>
    </button>
  );
}
