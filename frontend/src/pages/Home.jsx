import { useState, useEffect, useMemo } from 'react';
import BackButton from '../components/ui/BackButton';
import TariffCard from '../components/tariffs/TariffCard';
import HomePlanCard from '../components/home/HomePlanCard';
import HomeFeaturesBar from '../components/home/HomeFeaturesBar';
import LandingScene from '../components/home/LandingScene';
import { TariffCardSkeleton } from '../components/ui/Skeleton';
import { fetchTariffs } from '../utils/api';
import { groupTariffs, getMinPrice } from '../utils/tariffGroups';

const SECTIONS = {
  internet: { type: 'internet', title: 'Internet tariflari' },
  mobile: { type: 'mobile', title: 'Mobil tariflar' },
};

function WifiIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M5 12.55a11 11 0 0114.08 0M8.53 16.11a6 6 0 016.95 0M12 20h.01" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
      <path d="M2 8.82a15 15 0 0119.99 0" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
    </svg>
  );
}

function PhoneIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <rect x="5" y="2" width="14" height="20" rx="2" stroke="currentColor" strokeWidth="2" />
      <path d="M12 18h.01" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

export default function Home({
  onSelectTariff,
  scrollTarget,
  onScrollDone,
}) {
  const [tariffs, setTariffs] = useState([]);
  const [activeTab, setActiveTab] = useState('internet');
  const [selectedGroup, setSelectedGroup] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [internet, mobile] = await Promise.all([
          fetchTariffs('internet'),
          fetchTariffs('mobile'),
        ]);
        if (!cancelled) setTariffs([...internet, ...mobile]);
      } catch {
        /* silent */
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    if (!scrollTarget) return;
    if (scrollTarget === 'mobile-tariffs') setActiveTab('mobile');
    if (scrollTarget === 'internet-tariffs') setActiveTab('internet');
    onScrollDone?.();
  }, [scrollTarget, onScrollDone]);

  const activeSection = useMemo(() => {
    const meta = SECTIONS[activeTab];
    const filtered = tariffs.filter((t) => t.service_type === activeTab);
    const groups = groupTariffs(filtered, activeTab).map((g) => ({
      ...g,
      minPrice: getMinPrice(g.tariffs),
    }));
    return { ...meta, groups };
  }, [tariffs, activeTab]);

  const activeGroup = useMemo(() => {
    if (!selectedGroup) return null;
    return activeSection.groups.find((g) => g.id === selectedGroup) || null;
  }, [activeSection, selectedGroup]);

  const switchTab = (tab) => {
    setActiveTab(tab);
    setSelectedGroup(null);
  };

  const isLanding = !activeGroup;
  const pageClasses = [
    'page',
    'page--home',
    isLanding ? 'page--home-landing' : 'page--home-detail',
    `page--home-tab-${activeTab}`,
  ].join(' ');

  return (
    <div className={pageClasses}>
      {isLanding && <LandingScene />}

      <div className="landing-wrap">
        {isLanding && (
          <section className="landing-hero">
            <div className="service-toggle service-toggle--hero">
              <button
                type="button"
                className={`service-toggle__btn ${activeTab === 'internet' ? 'active' : ''}`}
                onClick={() => switchTab('internet')}
              >
                <WifiIcon />
                Internet ulash
              </button>
              <button
                type="button"
                className={`service-toggle__btn ${activeTab === 'mobile' ? 'active' : ''}`}
                onClick={() => switchTab('mobile')}
              >
                <PhoneIcon />
                Mobil raqam olish
              </button>
            </div>

            <h1 className="landing-hero__title">
              Tezkor, barqaror, cheksiz imkoniyatlar
              <br />
              endi <span className="landing-hero__gradient-text">yanada yaqin</span>
            </h1>
            <p className="landing-hero__subtitle">
              Eng yaxshi internet tariflarini tanlang va biz sizga bog&apos;lanamiz
            </p>
          </section>
        )}

        <section id="tariffs" className={`landing-plans ${isLanding ? '' : 'landing-plans--detail'}`}>
          {loading ? (
            <div className="plan-cards-grid">
              {Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="plan-card plan-card--skeleton">
                  <div className="skeleton skeleton--title" />
                  <div className="skeleton skeleton--line" />
                  <div className="skeleton skeleton--btn" />
                </div>
              ))}
            </div>
          ) : activeGroup ? (
            <div className="tariff-group-view">
              <BackButton
                onClick={() => setSelectedGroup(null)}
                label="Guruhlarga qaytish"
              />
              <h3 className="tariff-group-view__title">
                {activeGroup.icon} {activeGroup.title}
              </h3>
              <p className="tariff-group-view__desc">{activeGroup.description}</p>
              <div className="tariff-grid tariff-grid--home">
                {activeGroup.tariffs.map((t) => (
                  <TariffCard
                    key={t.id}
                    tariff={t}
                    onSelect={(tariff) => onSelectTariff?.(tariff)}
                  />
                ))}
              </div>
            </div>
          ) : (
            <div className={`plan-cards-grid plan-cards-grid--${activeTab}`}>
              {activeSection.groups.map((g) => (
                <HomePlanCard
                  key={g.id}
                  group={g}
                  onSelect={() => setSelectedGroup(g.id)}
                />
              ))}
            </div>
          )}
        </section>

        {isLanding && <HomeFeaturesBar />}
      </div>
    </div>
  );
}
