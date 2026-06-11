import { formatPrice } from '../../utils/format';

const THEMES = {
  blue: {
    iconBg: 'linear-gradient(145deg, #3b82f6 0%, #2563eb 100%)',
    cta: 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)',
    border: 'rgba(59, 130, 246, 0.45)',
    glow: 'rgba(59, 130, 246, 0.18)',
    shadow: '0 8px 40px rgba(59, 130, 246, 0.15)',
  },
  purple: {
    iconBg: 'linear-gradient(145deg, #a855f7 0%, #7c3aed 100%)',
    cta: 'linear-gradient(135deg, #a855f7 0%, #7c3aed 100%)',
    border: 'rgba(168, 85, 247, 0.45)',
    glow: 'rgba(168, 85, 247, 0.18)',
    shadow: '0 8px 40px rgba(168, 85, 247, 0.15)',
  },
  teal: {
    iconBg: 'linear-gradient(145deg, #14b8a6 0%, #0d9488 100%)',
    cta: 'linear-gradient(135deg, #14b8a6 0%, #0d9488 100%)',
    border: 'rgba(20, 184, 166, 0.45)',
    glow: 'rgba(20, 184, 166, 0.18)',
    shadow: '0 8px 40px rgba(20, 184, 166, 0.15)',
  },
  cyan: {
    iconBg: 'linear-gradient(145deg, #06b6d4 0%, #0891b2 100%)',
    cta: 'linear-gradient(135deg, #06b6d4 0%, #0891b2 100%)',
    border: 'rgba(6, 182, 212, 0.45)',
    glow: 'rgba(6, 182, 212, 0.18)',
    shadow: '0 8px 40px rgba(6, 182, 212, 0.15)',
  },
};

const GROUP_THEME = {
  'internet-home': 'blue',
  'internet-promo': 'purple',
  'internet-business': 'teal',
  'mobile-popular': 'blue',
  'mobile-ideal': 'purple',
  'mobile-data': 'cyan',
  'mobile-salom': 'purple',
  'mobile-special': 'teal',
  'mobile-business': 'teal',
};

const PLAN_ICONS = {
  'internet-home': (
    <svg width="26" height="26" viewBox="0 0 24 24" fill="none">
      <path d="M3 9.5L12 3l9 6.5V20a1 1 0 01-1 1H4a1 1 0 01-1-1V9.5z" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
      <path d="M9 21V12h6v9" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
    </svg>
  ),
  'internet-promo': (
    <svg width="26" height="26" viewBox="0 0 24 24" fill="none">
      <rect x="3" y="8" width="18" height="13" rx="1" stroke="currentColor" strokeWidth="2" />
      <path d="M12 8V21M3 12h18M12 8c-2-3-6-3-6 0s4 0 6 0 6-3 6 0-4 0-6 0z" stroke="currentColor" strokeWidth="2" />
    </svg>
  ),
  'internet-business': (
    <svg width="26" height="26" viewBox="0 0 24 24" fill="none">
      <rect x="2" y="7" width="20" height="14" rx="2" stroke="currentColor" strokeWidth="2" />
      <path d="M16 7V5a2 2 0 00-2-2h-4a2 2 0 00-2 2v2" stroke="currentColor" strokeWidth="2" />
      <path d="M12 12v.01" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  ),
  'mobile-popular': (
    <svg width="26" height="26" viewBox="0 0 24 24" fill="none">
      <rect x="7" y="2.5" width="10" height="19" rx="2.2" stroke="currentColor" strokeWidth="2" />
      <path d="M10.5 18h3" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <path d="M9.5 6.5h5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  ),
  'mobile-ideal': (
    <svg width="26" height="26" viewBox="0 0 24 24" fill="none">
      <path d="M12 3.2l2.6 5.2 5.8.85-4.2 4.1 1 5.75L12 16.38 6.8 19.1l1-5.75-4.2-4.1 5.8-.85L12 3.2z" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
    </svg>
  ),
  'mobile-data': (
    <svg width="26" height="26" viewBox="0 0 24 24" fill="none">
      <path d="M5 12.5a11 11 0 0114 0M8.5 16a6 6 0 017 0M12 20h.01" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" />
      <path d="M4 5h16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" opacity="0.65" />
    </svg>
  ),
  'mobile-salom': (
    <svg width="26" height="26" viewBox="0 0 24 24" fill="none">
      <path d="M4 11h16v9H4v-9z" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
      <path d="M12 11v9M4 15.5h16M12 11c-2.2-2.8-5.5-2.8-5.5-.4 0 1.4 1.6 1.8 5.5.4zm0 0c2.2-2.8 5.5-2.8 5.5-.4 0 1.4-1.6 1.8-5.5.4z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  ),
  'mobile-special': (
    <svg width="26" height="26" viewBox="0 0 24 24" fill="none">
      <path d="M16 21v-1.5a4 4 0 00-8 0V21" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <circle cx="12" cy="8" r="3.5" stroke="currentColor" strokeWidth="2" />
      <path d="M4 20v-.8a3 3 0 013-3M20 20v-.8a3 3 0 00-3-3" stroke="currentColor" strokeWidth="2" strokeLinecap="round" opacity="0.8" />
    </svg>
  ),
  'mobile-business': (
    <svg width="26" height="26" viewBox="0 0 24 24" fill="none">
      <rect x="3" y="7" width="18" height="13" rx="2" stroke="currentColor" strokeWidth="2" />
      <path d="M9 7V5a2 2 0 012-2h2a2 2 0 012 2v2M3 12h18M12 12v2" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  ),
};

function getMinSpeed(tariffs) {
  const speeds = tariffs
    .map((t) => {
      const m = (t.speed || '').match(/(\d+)/);
      return m ? parseInt(m[1], 10) : null;
    })
    .filter((s) => s != null);
  return speeds.length ? Math.min(...speeds) : null;
}

function getStats(group) {
  const count = group.tariffs?.length || 0;
  const minSpeed = getMinSpeed(group.tariffs || []);

  switch (group.id) {
    case 'internet-home':
      return [
        { icon: 'router', text: `${count} ta tarif` },
        { icon: 'gauge', text: minSpeed ? `${minSpeed} Mbps dan` : '100 Mbps dan' },
      ];
    case 'internet-promo':
      return [
        { icon: 'gift', text: `${count} ta tarif` },
        { icon: 'tag', text: 'Aksiyali narxlar' },
      ];
    case 'internet-business':
      return [
        { icon: 'user', text: `${count} ta tarif` },
        { icon: 'shield', text: 'Barqaror ulanish' },
      ];
    case 'mobile-popular':
      return [
        { icon: 'phone', text: `${count} ta tarif` },
        { icon: 'star', text: 'Ommabop' },
      ];
    case 'mobile-ideal':
      return [
        { icon: 'star', text: `${count} ta tarif` },
        { icon: 'shield', text: 'Premium' },
      ];
    case 'mobile-data':
      return [
        { icon: 'data', text: `${count} ta tarif` },
        { icon: 'gauge', text: 'Katta internet' },
      ];
    case 'mobile-salom':
      return [
        { icon: 'gift', text: `${count} ta tarif` },
        { icon: 'tag', text: 'Aksiya' },
      ];
    case 'mobile-special':
      return [
        { icon: 'users', text: `${count} ta tarif` },
        { icon: 'shield', text: 'Maxsus' },
      ];
    case 'mobile-business':
      return [
        { icon: 'briefcase', text: `${count} ta tarif` },
        { icon: 'tool', text: 'Biznes aloqa' },
      ];
    default:
      return [
        { icon: 'router', text: `${count} ta tarif` },
        { icon: 'gauge', text: 'Eng yaxshi narxlar' },
      ];
  }
}

const STAT_ICONS = {
  router: (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
      <rect x="2" y="6" width="20" height="12" rx="2" stroke="currentColor" strokeWidth="2" />
      <path d="M6 10h.01M10 10h.01M6 14h12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  ),
  gauge: (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
      <path d="M12 14l3-3" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <path d="M12 2a10 10 0 100 20 10 10 0 000-20z" stroke="currentColor" strokeWidth="2" />
      <path d="M12 6v2" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  ),
  gift: (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
      <rect x="3" y="8" width="18" height="13" rx="1" stroke="currentColor" strokeWidth="2" />
      <path d="M12 8V21M3 12h18" stroke="currentColor" strokeWidth="2" />
    </svg>
  ),
  tag: (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
      <path d="M20.59 13.41l-7.17 7.17a2 2 0 01-2.83 0L2 12V2h10l8.59 8.59a2 2 0 010 2.82z" stroke="currentColor" strokeWidth="2" />
    </svg>
  ),
  user: (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
      <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <circle cx="12" cy="7" r="4" stroke="currentColor" strokeWidth="2" />
    </svg>
  ),
  shield: (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" stroke="currentColor" strokeWidth="2" />
      <path d="M9 12l2 2 4-4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  ),
  phone: (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
      <rect x="7" y="2.5" width="10" height="19" rx="2.2" stroke="currentColor" strokeWidth="2" />
      <path d="M11 18h2" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  ),
  star: (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
      <path d="M12 3.5l2.35 4.75 5.25.76-3.8 3.7.9 5.22L12 15.46l-4.7 2.47.9-5.22-3.8-3.7 5.25-.76L12 3.5z" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
    </svg>
  ),
  data: (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
      <path d="M5 12.5a11 11 0 0114 0M8.5 16a6 6 0 017 0M12 20h.01" stroke="currentColor" strokeWidth="2.3" strokeLinecap="round" />
    </svg>
  ),
  users: (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
      <path d="M16 21v-1a4 4 0 00-8 0v1" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <circle cx="12" cy="8" r="3.5" stroke="currentColor" strokeWidth="2" />
      <path d="M5 20v-.6A3 3 0 018 16M19 20v-.6A3 3 0 0016 16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  ),
  briefcase: (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
      <rect x="3" y="7" width="18" height="13" rx="2" stroke="currentColor" strokeWidth="2" />
      <path d="M9 7V5a2 2 0 012-2h2a2 2 0 012 2v2M3 12h18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  ),
  tool: (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
      <path d="M14.7 6.3a4 4 0 004.8 4.8l-7.2 7.2a2.2 2.2 0 01-3.1 0l-3.5-3.5a2.2 2.2 0 010-3.1l7.2-7.2a4 4 0 001.8 1.8z" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
    </svg>
  ),
};

export default function HomePlanCard({ group, onSelect }) {
  const themeKey = GROUP_THEME[group.id] || 'blue';
  const theme = THEMES[themeKey];
  const stats = getStats(group);
  const minPrice = group.minPrice;
  const icon = PLAN_ICONS[group.id] || (
    <span style={{ fontSize: 26 }}>{group.icon}</span>
  );

  return (
    <article
      className={`plan-card plan-card--${themeKey}`}
      style={{
        '--plan-border': theme.border,
        '--plan-glow': theme.glow,
        '--plan-shadow': theme.shadow,
        '--plan-cta': theme.cta,
        '--plan-icon-bg': theme.iconBg,
      }}
    >
      <div className="plan-card__inner">
        <div className="plan-card__icon">{icon}</div>
        <h3 className="plan-card__title">{group.title}</h3>
        <p className="plan-card__desc">{group.description}</p>
        <div className="plan-card__stats">
          {stats.map((s) => (
            <span key={s.text} className="plan-card__stat">
              {STAT_ICONS[s.icon]}
              {s.text}
            </span>
          ))}
        </div>
        <button
          type="button"
          className="plan-card__cta"
          onClick={() => onSelect?.(group)}
        >
          <span>
            {minPrice != null
              ? (minPrice === 0 ? 'Bepul' : `${formatPrice(minPrice)} dan`)
              : 'Tanlash'}
          </span>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path d="M5 12h14M13 6l6 6-6 6" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
      </div>
    </article>
  );
}
