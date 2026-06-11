import BackButton from '../components/ui/BackButton';
import Button from '../components/ui/Button';
import StepProgress from '../components/ui/StepProgress';
import ServiceCard from '../components/services/ServiceCard';

export default function ServiceSelection({ selected, onSelect, onContinue, onBack }) {
  return (
    <div className="page page--flow">
      <div className="flow-card">
        <BackButton onClick={onBack} label="Bosh sahifa" />
        <StepProgress current="service" />

        <h1 className="flow-title">Xizmat turini tanlang</h1>
        <p className="flow-subtitle">Davom etish uchun internet yoki mobil xizmatni tanlang</p>

        <div className="service-grid">
          <ServiceCard
            type="internet"
            title="Internet"
            description="Optik tolali GPON texnologiyasi asosida yuqori tezlikdagi uy interneti"
            icon="🌐"
            selected={selected === 'internet'}
            onSelect={onSelect}
          />
          <ServiceCard
            type="mobile"
            title="Mobil"
            description="O'zbekiston bo'ylab 4G/5G tarmoqlari, qulay daqiqa va gigabaytlar"
            icon="📱"
            selected={selected === 'mobile'}
            onSelect={onSelect}
          />
        </div>

        <div className="flow-actions">
          <Button
            variant="primary"
            size="lg"
            disabled={!selected}
            onClick={onContinue}
          >
            Davom etish
          </Button>
        </div>
      </div>
    </div>
  );
}
