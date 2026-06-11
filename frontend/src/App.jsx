import { useEffect, useState } from 'react';
import Layout from './components/layout/Layout';
import Home from './pages/Home';
import ServiceSelection from './pages/ServiceSelection';
import TariffSelection from './pages/TariffSelection';
import ApplicationForm from './pages/ApplicationForm';
import SessionCreating from './pages/SessionCreating';
import ClientChat from './pages/ClientChat';
import SessionCompleted from './pages/SessionCompleted';

export default function App() {
  const [page, setPage] = useState('home');
  const [serviceType, setServiceType] = useState(null);
  const [selectedTariff, setSelectedTariff] = useState(null);
  const [sessionInfo, setSessionInfo] = useState(null);
  const [scrollTarget, setScrollTarget] = useState(null);

  useEffect(() => {
    const preventCtrlWheelZoom = (event) => {
      if (event.ctrlKey) {
        event.preventDefault();
      }
    };

    const preventKeyboardZoom = (event) => {
      if (!(event.ctrlKey || event.metaKey)) return;
      if (['+', '-', '=', '0'].includes(event.key)) {
        event.preventDefault();
      }
    };

    window.addEventListener('wheel', preventCtrlWheelZoom, { passive: false });
    window.addEventListener('keydown', preventKeyboardZoom);

    return () => {
      window.removeEventListener('wheel', preventCtrlWheelZoom);
      window.removeEventListener('keydown', preventKeyboardZoom);
    };
  }, []);

  const handleSelectService = (type) => {
    setServiceType(type);
    setSelectedTariff(null);
    setPage('service');
  };

  const handleSelectTariffFromHome = (tariff) => {
    setServiceType(tariff.service_type);
    setSelectedTariff(tariff);
    setPage('form');
  };

  const handleServiceContinue = () => {
    if (serviceType) setPage('tariffs');
  };

  const handleTariffContinue = () => {
    if (selectedTariff) setPage('form');
  };

  const handleFormSuccess = (info) => {
    setSessionInfo(info);
    setPage('sessionCreating');
  };

  const handleNavHome = () => {
    setScrollTarget(null);
    setSessionInfo(null);
    setPage('home');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleSessionReady = (info) => {
    setSessionInfo((prev) => ({
      ...prev,
      ...info,
      tariff: prev?.tariff || selectedTariff,
      application_type: info?.application_type || prev?.application_type || serviceType,
    }));
    setPage('chat');
  };

  const handleSessionCompleted = (info) => {
    setSessionInfo((prev) => ({
      ...prev,
      ...info,
      tariff: prev?.tariff || selectedTariff,
      completed_at: new Date().toISOString(),
    }));
    setPage('completed');
  };

  const renderPage = () => {
    switch (page) {
      case 'home':
        return (
          <Home
            onSelectService={handleSelectService}
            onSelectTariff={handleSelectTariffFromHome}
            scrollTarget={scrollTarget}
            onScrollDone={() => setScrollTarget(null)}
          />
        );
      case 'service':
        return (
          <ServiceSelection
            selected={serviceType}
            onSelect={setServiceType}
            onContinue={handleServiceContinue}
            onBack={handleNavHome}
          />
        );
      case 'tariffs':
        return (
          <TariffSelection
            serviceType={serviceType}
            selectedTariff={selectedTariff}
            onSelect={setSelectedTariff}
            onContinue={handleTariffContinue}
            onBack={() => setPage('service')}
          />
        );
      case 'form':
        return (
          <ApplicationForm
            serviceType={serviceType}
            tariff={selectedTariff}
            onBack={() => setPage('tariffs')}
            onSubmitSuccess={handleFormSuccess}
          />
        );
      case 'sessionCreating':
        return (
          <SessionCreating
            sessionId={sessionInfo?.session_id}
            onReady={handleSessionReady}
          />
        );
      case 'chat':
        if (!sessionInfo) return null;
        return (
          <ClientChat
            sessionInfo={sessionInfo}
            onSessionCompleted={handleSessionCompleted}
            onSessionExpired={handleSessionCompleted}
          />
        );
      case 'completed':
        return (
          <SessionCompleted
            sessionInfo={sessionInfo}
            onRestart={handleNavHome}
          />
        );
      default:
        return <Home onSelectService={handleSelectService} />;
    }
  };

  return (
    <Layout fullWidth={page === 'home' || page === 'chat'} home={page === 'home'}>
      {renderPage()}
    </Layout>
  );
}
