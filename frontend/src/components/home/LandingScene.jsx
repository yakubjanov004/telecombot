export default function LandingScene() {
  return (
    <div className="landing-scene" aria-hidden="true">
      <div className="landing-scene__img landing-scene__img--left" />
      <div className="landing-scene__img landing-scene__img--right" />

      <div className="landing-scene__vignette" />

      <svg className="landing-scene__arc" viewBox="0 0 1200 400" preserveAspectRatio="none">
        <defs>
          <linearGradient id="fiberGrad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#06b6d4" stopOpacity="0.9" />
            <stop offset="50%" stopColor="#8b5cf6" stopOpacity="1" />
            <stop offset="100%" stopColor="#3b82f6" stopOpacity="0.9" />
          </linearGradient>
          <filter id="fiberGlow">
            <feGaussianBlur stdDeviation="4" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>
        <path
          d="M 80 320 C 300 80, 900 80, 1120 320"
          fill="none"
          stroke="url(#fiberGrad)"
          strokeWidth="3"
          filter="url(#fiberGlow)"
          opacity="0.85"
        />
        <path
          d="M 80 328 C 300 88, 900 88, 1120 328"
          fill="none"
          stroke="url(#fiberGrad)"
          strokeWidth="1.5"
          opacity="0.4"
        />
      </svg>

      <div className="landing-scene__tv-badge">4K</div>

      <div className="landing-scene__wifi">
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
          <path d="M5 12.55a11 11 0 0114.08 0M8.53 16.11a6 6 0 016.95 0M12 20h.01" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
          <path d="M2 8.82a15 15 0 0119.99 0" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
        </svg>
      </div>

      <div className="landing-scene__fiber-bundle">
        <div className="landing-scene__cables">
          {['#06b6d4', '#3b82f6', '#8b5cf6', '#06b6d4', '#a855f7', '#22d3ee'].map((c, i) => (
            <span key={i} style={{ '--cable-color': c, '--cable-i': i }} />
          ))}
        </div>
        <span className="landing-scene__fiber-label">
          <strong>Fiber Optic</strong>
          <small>Texnologiya</small>
        </span>
      </div>

      <div className="landing-scene__speed">
        <div className="landing-scene__speed-icons">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
            <rect x="2" y="3" width="20" height="14" rx="2" stroke="currentColor" strokeWidth="2" />
            <path d="M8 21h8M12 17v4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          </svg>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" />
            <path d="M2 12h20M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10 15.3 15.3 0 014-10z" stroke="currentColor" strokeWidth="2" />
          </svg>
        </div>
        <div className="landing-scene__speed-text">
          <strong>1000 Mbps</strong>
          <small>gacha</small>
        </div>
      </div>
    </div>
  );
}
