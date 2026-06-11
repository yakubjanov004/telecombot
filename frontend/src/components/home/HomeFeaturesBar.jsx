const FEATURES = [
  {
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 00-2.91-.09z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M12 15l-3-3a22 22 0 012-3.95A12.88 12.88 0 0122 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 01-4 2z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
    title: 'Tezkor ulanish',
    desc: "Arizangizdan so'ng tezda bog'lanamiz",
  },
  {
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path d="M3 11h3a2 2 0 012 2v3a2 2 0 01-2 2H5a2 2 0 01-2-2v-5z" stroke="currentColor" strokeWidth="2" />
        <path d="M3 11a9 9 0 019-9 9 9 0 019 9" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
        <path d="M12 20v-3a2 2 0 012-2h3" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      </svg>
    ),
    title: 'Jonli operator',
    desc: 'Mutaxassislarimiz sizga yordam beradi',
  },
  {
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
    title: 'Xavfsiz va ishonchli',
    desc: "Ma'lumotlaringiz himoyalangan",
  },
  {
    icon: (
      <span className="home-features__24">24</span>
    ),
    title: "24/7 qo'llab-quvvatlash",
    desc: "Istalgan vaqtda bog'lanishingiz mumkin",
  },
];

export default function HomeFeaturesBar() {
  return (
    <div className="home-features">
      {FEATURES.map((f) => (
        <div key={f.title} className="home-features__item">
          <div className="home-features__icon">{f.icon}</div>
          <div className="home-features__text">
            <div className="home-features__title">{f.title}</div>
            <div className="home-features__desc">{f.desc}</div>
          </div>
        </div>
      ))}
    </div>
  );
}
