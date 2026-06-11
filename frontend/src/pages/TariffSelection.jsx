import { useState, useEffect, useMemo } from 'react';
import BackButton from '../components/ui/BackButton';
import Button from '../components/ui/Button';
import StepProgress from '../components/ui/StepProgress';
import TariffCard from '../components/tariffs/TariffCard';
import TariffGroupCard from '../components/tariffs/TariffGroupCard';
import { TariffCardSkeleton } from '../components/ui/Skeleton';
import { fetchTariffs } from '../utils/api';
import { groupTariffs, getMinPrice } from '../utils/tariffGroups';

export default function TariffSelection({
  serviceType,
  selectedTariff,
  onSelect,
  onContinue,
  onBack,
}) {
  const [tariffs, setTariffs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedGroup, setSelectedGroup] = useState(null);
  const [detailTariff, setDetailTariff] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        setLoading(true);
        setError('');
        const data = await fetchTariffs(serviceType);
        if (!cancelled) setTariffs(data);
      } catch {
        if (!cancelled) setError('Tariflarni yuklashda xatolik');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [serviceType]);

  const groups = useMemo(() => {
    return groupTariffs(tariffs, serviceType).map((g) => ({
      ...g,
      minPrice: getMinPrice(g.tariffs),
    }));
  }, [tariffs, serviceType]);

  const activeGroup = useMemo(() => {
    if (!selectedGroup) return null;
    return groups.find((g) => g.id === selectedGroup) || null;
  }, [groups, selectedGroup]);

  const title = serviceType === 'internet' ? 'Internet tariflari' : 'Mobil tariflar';

  return (
    <div className="page page--flow page--wide">
      <div className="flow-card flow-card--wide">
        <BackButton
          onClick={selectedGroup ? () => setSelectedGroup(null) : onBack}
          label={selectedGroup ? 'Guruhlarga qaytish' : undefined}
        />
        <StepProgress current="tariffs" />

        <h1 className="flow-title">{title}</h1>
        <p className="flow-subtitle">
          {selectedGroup
            ? 'Sizga mos tarif rejasini tanlang'
            : 'Avval tarif guruhini tanlang'}
        </p>

        {error && <div className="alert alert--error">{error}</div>}

        {loading ? (
          <div className="tariff-grid">
            {Array.from({ length: 3 }).map((_, i) => <TariffCardSkeleton key={i} />)}
          </div>
        ) : selectedGroup && activeGroup ? (
          <>
            <h3 className="tariff-group-view__title tariff-group-view__title--flow">
              {activeGroup.icon} {activeGroup.title}
            </h3>
            <div className="tariff-grid">
              {activeGroup.tariffs.map((t) => (
                <TariffCard
                  key={t.id}
                  tariff={t}
                  selected={selectedTariff?.id === t.id}
                  onSelect={onSelect}
                  onDetails={setDetailTariff}
                />
              ))}
            </div>
          </>
        ) : (
          <div className="tariff-groups-grid">
            {groups.map((g) => (
              <TariffGroupCard
                key={g.id}
                group={g}
                onSelect={() => setSelectedGroup(g.id)}
              />
            ))}
          </div>
        )}

        <div className="flow-actions flow-actions--sticky">
          <Button
            variant="primary"
            size="lg"
            disabled={!selectedTariff}
            onClick={onContinue}
          >
            {selectedTariff ? `${selectedTariff.name} — Davom etish` : 'Tarif tanlang'}
          </Button>
        </div>
      </div>

      {detailTariff && (
        <div className="modal-overlay" onClick={() => setDetailTariff(null)} role="dialog" aria-modal="true">
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <button type="button" className="modal-close" onClick={() => setDetailTariff(null)} aria-label="Yopish">×</button>
            <TariffCard
              tariff={detailTariff}
              selected={selectedTariff?.id === detailTariff.id}
              onSelect={(t) => { onSelect(t); setDetailTariff(null); }}
            />
          </div>
        </div>
      )}
    </div>
  );
}
