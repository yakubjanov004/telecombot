import { useState } from 'react';
import Button from '../ui/Button';

const NAV_ITEMS = [
  { id: 'tariffs', label: 'Tariflar' },
];

export default function Header({
  onNavHome,
  onNavSection,
  onStartApplication,
  compact = false,
}) {
  const [menuOpen, setMenuOpen] = useState(false);

  const handleNavClick = (id) => {
    setMenuOpen(false);
    onNavSection?.(id);
  };

  const handleApply = () => {
    setMenuOpen(false);
    onStartApplication?.();
  };

  return (
    <header className={`site-header ${compact ? 'site-header--compact' : ''}`}>
      <button type="button" className="site-header__brand" onClick={onNavHome} aria-label="Bosh sahifa">
        <div className="site-header__logo" aria-hidden="true">
          <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
            <rect width="32" height="32" rx="8" fill="url(#logoGrad)" />
            <path d="M16 8l8 12h-6v8h-4v-8H8L16 8z" fill="white" />
            <defs>
              <linearGradient id="logoGrad" x1="0" y1="0" x2="32" y2="32">
                <stop stopColor="#06b6d4" />
                <stop offset="1" stopColor="#4f46e5" />
              </linearGradient>
            </defs>
          </svg>
        </div>
        <span className="site-header__name">Uztelecom</span>
      </button>

      {!compact && (
        <>
          <nav className="site-header__nav" aria-label="Asosiy navigatsiya">
            {NAV_ITEMS.map((item) => (
              <button
                key={item.id}
                type="button"
                className="site-header__link"
                onClick={() => handleNavClick(item.id)}
              >
                {item.label}
              </button>
            ))}
          </nav>

          <div className="site-header__actions">
            <a href="tel:+998712026060" className="site-header__phone">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path d="M22 16.92v3a2 2 0 01-2.18 2 19.79 19.79 0 01-8.63-3.07 19.5 19.5 0 01-6-6 19.79 19.79 0 01-3.07-8.67A2 2 0 014.11 2h3a2 2 0 012 1.72c.127.96.361 1.903.7 2.81a2 2 0 01-.45 2.11L8.09 9.91a16 16 0 006 6l1.27-1.27a2 2 0 012.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0122 16.92z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              <span>+998 71 202 60 60</span>
            </a>
            <Button variant="primary" size="sm" className="site-header__cta" onClick={handleApply}>
              Ariza qoldirish
            </Button>
          </div>

          <button
            type="button"
            className="site-header__burger"
            onClick={() => setMenuOpen(!menuOpen)}
            aria-label="Menyu"
            aria-expanded={menuOpen}
          >
            <span /><span /><span />
          </button>

          {menuOpen && (
            <div className="site-header__mobile-menu">
              {NAV_ITEMS.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  className="site-header__mobile-link"
                  onClick={() => handleNavClick(item.id)}
                >
                  {item.label}
                </button>
              ))}
              <a href="tel:+998712026060" className="site-header__mobile-phone">
                📞 +998 71 202 60 60
              </a>
              <Button variant="primary" size="lg" className="site-header__mobile-cta" onClick={handleApply}>
                Ariza qoldirish
              </Button>
            </div>
          )}
        </>
      )}
    </header>
  );
}
