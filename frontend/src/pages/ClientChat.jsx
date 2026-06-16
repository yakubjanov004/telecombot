import { useState, useEffect, useRef, useCallback } from 'react';
import useWebSocket from '../hooks/useWebSocket';
import ConnectionStatus from '../components/chat/ConnectionStatus';
import ChatBubble from '../components/chat/ChatBubble';
import ChatInput from '../components/chat/ChatInput';
import TypingIndicator from '../components/chat/TypingIndicator';
import { closeChatSession, uploadChatImage } from '../utils/api';

export default function ClientChat({ sessionInfo, onSessionExpired, onSessionCompleted }) {
  const { session_id: sessionId, client_name: clientName } = sessionInfo;
  const fallbackParts = String(clientName || '').split('/').map((part) => part.trim()).filter(Boolean);
  const headerLocation = sessionInfo.location || fallbackParts[0];
  const headerTariff = sessionInfo.tariff?.name || sessionInfo.tariff_name || fallbackParts[1];
  const headerTitle = headerLocation && headerTariff
    ? `${headerLocation} · ${headerTariff}`
    : clientName || 'Mijoz';
  const [inputText, setInputText] = useState('');
  const [uploading, setUploading] = useState(false);
  const [closing, setClosing] = useState(false);
  const [focusToken, setFocusToken] = useState(0);
  const [lightboxImg, setLightboxImg] = useState(null);
  const [showTyping, setShowTyping] = useState(false);
  const messagesEndRef = useRef(null);

  const handleExpired = useCallback(() => {
    const handler = onSessionCompleted || onSessionExpired;
    handler?.(sessionInfo);
  }, [onSessionCompleted, onSessionExpired, sessionInfo]);

  const handleOperatorConnected = useCallback(() => {
    setShowTyping(false);
  }, []);

  const {
    messages,
    connectionState,
    operatorOnline,
    isCooldown,
    cooldownSec,
    sendMessage,
  } = useWebSocket(sessionId, {
    onExpired: handleExpired,
    onOperatorConnected: handleOperatorConnected,
  });

  const visibleMessages = messages.filter((msg) => {
    if (msg.sender === 'bot') return false;
    if (msg.sender === 'operator' && msg.message?.trim() === 'Operator qabul qildi') return false;
    return true;
  });

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, showTyping]);

  useEffect(() => {
    if (!operatorOnline && connectionState === 'connected') {
      const timer = setTimeout(() => setShowTyping(true), 4000);
      return () => clearTimeout(timer);
    }
    setShowTyping(false);
  }, [operatorOnline, connectionState]);

  const handleSend = () => {
    if (sendMessage(inputText)) {
      setInputText('');
      setFocusToken((value) => value + 1);
      return true;
    }
    return false;
  };

  const handleImageUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    try {
      const data = await uploadChatImage(file);
      sendMessage('', data.url);
      setFocusToken((value) => value + 1);
    } catch (err) {
      alert(err.message);
    } finally {
      setUploading(false);
      e.target.value = '';
    }
  };

  const handleCloseChat = async () => {
    if (closing) return;

    setClosing(true);
    try {
      await closeChatSession(sessionId);
      const handler = onSessionCompleted || onSessionExpired;
      handler?.({ ...sessionInfo, closed_reason: 'cancelled' });
    } catch (err) {
      alert(err.message);
      setClosing(false);
    }
  };

  return (
    <div className="chat-page">
      <header className="chat-header">
        <div className="chat-header__inner">
          <div className="chat-header__info">
            <div className="chat-header__avatar" aria-hidden="true">
              {clientName?.charAt(0)?.toUpperCase() || 'M'}
            </div>
            <div>
              <h1 className="chat-header__name">{headerTitle}</h1>
              <ConnectionStatus state={connectionState} operatorOnline={operatorOnline} />
            </div>
          </div>
          <button
            type="button"
            className="chat-header__end"
            onClick={handleCloseChat}
            disabled={closing || connectionState === 'expired'}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path d="M6 6l12 12M18 6L6 18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
            {closing ? 'Tugatilmoqda...' : 'Chatni tugatish'}
          </button>
        </div>
      </header>

      <div className="chat-body">
        <div className="chat-messages">
          <div className="chat-thread" role="log" aria-live="polite" aria-label="Chat xabarlari">
            {visibleMessages.length === 0 && (
              <div className="chat-empty">
                <p>Lokatsiya va tarif operatorga yuborildi.</p>
                <p className="chat-empty__hint">Savolingiz bo'lsa, shu chatga yozing yoki rasm yuboring.</p>
              </div>
            )}
            {visibleMessages.map((msg) => (
              <ChatBubble key={msg.id} message={msg} onImageClick={setLightboxImg} />
            ))}
            <TypingIndicator visible={showTyping && !operatorOnline} />
            <div ref={messagesEndRef} />
          </div>
        </div>

        <ChatInput
          value={inputText}
          onChange={setInputText}
          onSend={handleSend}
          onImageUpload={handleImageUpload}
          disabled={closing || connectionState === 'failed' || connectionState === 'expired'}
          uploading={uploading}
          isCooldown={isCooldown}
          cooldownSec={cooldownSec}
          focusToken={focusToken}
        />
      </div>

      {lightboxImg && (
        <div className="lightbox" onClick={() => setLightboxImg(null)} role="dialog" aria-modal="true">
          <div className="lightbox__content" onClick={(e) => e.stopPropagation()}>
            <button type="button" className="lightbox__close" onClick={() => setLightboxImg(null)} aria-label="Yopish">×</button>
            <img src={lightboxImg} alt="Kattalashtirilgan rasm" />
          </div>
        </div>
      )}
    </div>
  );
}
