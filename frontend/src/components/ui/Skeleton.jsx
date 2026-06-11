export function Skeleton({ className = '', style }) {
  return <div className={`skeleton ${className}`} style={style} aria-hidden="true" />;
}

export function TariffCardSkeleton() {
  return (
    <div className="tariff-card tariff-card--skeleton">
      <Skeleton className="skeleton--title" />
      <Skeleton className="skeleton--price" />
      <Skeleton className="skeleton--line" />
      <Skeleton className="skeleton--line" />
      <Skeleton className="skeleton--btn" />
    </div>
  );
}
