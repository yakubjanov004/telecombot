export default function ServiceCard({ type, title, description, icon, selected, onSelect }) {
  return (
    <button
      type="button"
      className={`service-card ${selected ? 'service-card--selected' : ''} service-card--${type}`}
      onClick={() => onSelect(type)}
      aria-pressed={selected}
    >
      <div className="service-card__icon" aria-hidden="true">{icon}</div>
      <h3 className="service-card__title">{title}</h3>
      <p className="service-card__desc">{description}</p>
      <div className="service-card__check">
        {selected ? (
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="10" fill="currentColor" />
            <path d="M8 12l3 3 5-6" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        ) : (
          <div className="service-card__ring" />
        )}
      </div>
    </button>
  );
}
