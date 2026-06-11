const STEPS = [
  { key: 'service', label: 'Xizmat' },
  { key: 'tariffs', label: 'Tarif' },
  { key: 'form', label: 'Ariza' },
  { key: 'chat', label: 'Chat' },
];

export default function StepProgress({ current }) {
  const currentIndex = STEPS.findIndex((s) => s.key === current);

  return (
    <nav className="step-progress" aria-label="Jarayon bosqichlari">
      {STEPS.map((step, i) => {
        const isActive = i === currentIndex;
        const isDone = i < currentIndex;
        return (
          <div key={step.key} className={`step-progress__item ${isActive ? 'active' : ''} ${isDone ? 'done' : ''}`}>
            <div className="step-progress__dot" aria-hidden="true">
              {isDone ? '✓' : i + 1}
            </div>
            <span className="step-progress__label">{step.label}</span>
            {i < STEPS.length - 1 && <div className="step-progress__line" aria-hidden="true" />}
          </div>
        );
      })}
    </nav>
  );
}
