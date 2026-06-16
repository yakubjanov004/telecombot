import { useState } from 'react';
import BackButton from '../components/ui/BackButton';
import Button from '../components/ui/Button';
import StepProgress from '../components/ui/StepProgress';
import FormField from '../components/forms/FormField';
import { formatPrice } from '../utils/format';
import {
  createSession,
  submitInternetApplication,
  submitMobileApplication
} from '../utils/api';

function cleanValue(value) {
  return String(value || '').replace(/\u00a0/g, ' ').replace(/\s+/g, ' ').trim();
}

function optionalInt(value) {
  if (value == null || value === '') return undefined;
  const numberValue = Number(value);
  return Number.isInteger(numberValue) ? numberValue : undefined;
}

export default function ApplicationForm({
  serviceType,
  tariff,
  onBack,
  onSubmitSuccess,
}) {
  const [region, setRegion] = useState('');
  const [msisdn, setMsisdn] = useState('');
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);
  const [apiError, setApiError] = useState('');
  const isMobile = serviceType === 'mobile';
  const regionLabel = isMobile ? 'Hudud' : 'Lokatsiya';
  const regionError = isMobile ? 'Hududni kiriting' : 'Lokatsiyani kiriting';

  const validate = () => {
    const nextErrors = {};
    if (!cleanValue(region)) {
      nextErrors.region = regionError;
    }
    if (isMobile && !cleanValue(msisdn)) {
      nextErrors.msisdn = 'Tanlamoqchi bo\'lgan raqamni kiriting';
    }
    setErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validate()) return;

    setLoading(true);
    setApiError('');

    const selectedTariffId = optionalInt(tariff?.id);
    const payload = {
      branches: cleanValue(region),
      rate_plan_first_connection: tariff?.name || '',
      selected_tariff_code: tariff?.name,
    };
    if (selectedTariffId !== undefined) {
      payload.selected_tariff_id = selectedTariffId;
    }
    if (isMobile) {
      payload.msisdn = cleanValue(msisdn);
    }

    try {
      const appResponse = isMobile
        ? await submitMobileApplication(payload)
        : await submitInternetApplication(payload);

      const session = await createSession({
        client_name: isMobile
          ? `${payload.branches} / ${payload.msisdn}`
          : `${payload.branches} / ${payload.rate_plan_first_connection}`,
        phone: isMobile ? payload.msisdn : null,
        application_type: serviceType,
        application_id: appResponse.id,
      });

      onSubmitSuccess({
        ...session,
        application_type: serviceType,
        location: payload.branches,
        tariff_name: payload.rate_plan_first_connection,
        requested_number: payload.msisdn,
        tariff,
      });
    } catch (err) {
      setApiError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page page--flow">
      <div className="form-layout">
        <div className="flow-card">
          <BackButton onClick={onBack} />
          <StepProgress current="form" />

          <h1 className="flow-title">{isMobile ? 'Mobil raqam olish' : 'Internet ulash'}</h1>
          <p className="flow-subtitle">
            {isMobile
              ? 'Hudud va tanlamoqchi bo\'lgan raqamni kiriting'
              : 'Tanlangan tarif uchun lokatsiyani kiriting'}
          </p>

          {apiError && <div className="alert alert--error">{apiError}</div>}

          <form onSubmit={handleSubmit} className="application-form" noValidate>
            <FormField
              label={regionLabel}
              id="region"
              error={errors.region}
              required
            >
              <input
                id="region"
                className="input"
                value={region}
                onChange={(e) => {
                  setRegion(e.target.value);
                  if (errors.region) setErrors((current) => ({ ...current, region: undefined }));
                }}
                placeholder={isMobile ? 'Masalan: Toshkent sh.' : 'Masalan: Toshkent sh., Yunusobod'}
                autoComplete="address-level1"
              />
            </FormField>

            {isMobile && (
              <FormField
                label="Tanlamoqchi bo'lgan raqam"
                id="msisdn"
                error={errors.msisdn}
                required
              >
                <input
                  id="msisdn"
                  className="input"
                  value={msisdn}
                  onChange={(e) => {
                    setMsisdn(e.target.value.replace(/[^\d+]/g, '').slice(0, 13));
                    if (errors.msisdn) setErrors((current) => ({ ...current, msisdn: undefined }));
                  }}
                  placeholder="998901234567"
                  inputMode="tel"
                  autoComplete="tel"
                />
              </FormField>
            )}

            <Button
              type="submit"
              variant="primary"
              size="lg"
              className="application-form__submit"
              disabled={loading}
            >
              {loading ? 'Ulanmoqda...' : 'Operatorga ulanish'}
            </Button>
          </form>
        </div>

        <aside className="tariff-summary">
          <h3>Tanlangan tarif</h3>
          <div className="tariff-summary__card">
            <div className="tariff-summary__type">
              {serviceType === 'internet' ? 'Internet' : 'Mobil'}
            </div>
            <div className="tariff-summary__name">{tariff?.name}</div>
            <div className="tariff-summary__price">{formatPrice(tariff?.price)}</div>
            <ul className="tariff-summary__specs">
              {serviceType === 'internet' ? (
                <>
                  <li><span>Tezlik</span><strong>{tariff?.speed || '50 Mbps'}</strong></li>
                  <li><span>Trafik</span><strong>Cheksiz</strong></li>
                </>
              ) : (
                <>
                  <li><span>Internet</span><strong>{tariff?.mb || '-'}</strong></li>
                  <li><span>Daqiqalar</span><strong>{tariff?.minutes || '-'}</strong></li>
                  <li><span>SMS</span><strong>{tariff?.sms || '-'}</strong></li>
                </>
              )}
            </ul>
          </div>
        </aside>
      </div>
    </div>
  );
}
