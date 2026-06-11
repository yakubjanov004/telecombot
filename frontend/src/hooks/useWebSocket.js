import { useState, useEffect, useRef, useCallback } from 'react';

const MAX_RECONNECT = 5;
const RECONNECT_DELAY = 3000;

export default function useWebSocket(sessionId, { onExpired, onOperatorConnected } = {}) {
  const [messages, setMessages] = useState([]);
  const [connectionState, setConnectionState] = useState('connecting');
  const [operatorOnline, setOperatorOnline] = useState(false);
  const [isCooldown, setIsCooldown] = useState(false);
  const [cooldownSec, setCooldownSec] = useState(0);

  const socketRef = useRef(null);
  const cooldownTimerRef = useRef(null);
  const reconnectTimerRef = useRef(null);
  const reconnectAttemptsRef = useRef(0);
  const expiredRef = useRef(false);
  const shouldReconnectRef = useRef(false);
  const handlersRef = useRef({ onExpired, onOperatorConnected });

  useEffect(() => {
    handlersRef.current = { onExpired, onOperatorConnected };
  }, [onExpired, onOperatorConnected]);

  const triggerCooldown = useCallback((seconds) => {
    setIsCooldown(true);
    setCooldownSec(seconds);
    if (cooldownTimerRef.current) clearInterval(cooldownTimerRef.current);

    let rem = seconds;
    cooldownTimerRef.current = setInterval(() => {
      rem -= 1;
      if (rem <= 0) {
        clearInterval(cooldownTimerRef.current);
        cooldownTimerRef.current = null;
        setIsCooldown(false);
        setCooldownSec(0);
      } else {
        setCooldownSec(rem);
      }
    }, 1000);
  }, []);

  const addMessage = useCallback((msg) => {
    setMessages((prev) => {
      const exists = prev.some(
        (m) => m.message === msg.message && m.media_url === msg.media_url && m.sender === msg.sender
      );
      if (exists) return prev;
      return [...prev, msg];
    });
  }, []);

  const connect = useCallback(() => {
    if (!sessionId || expiredRef.current) return;

    const currentSocket = socketRef.current;
    if (
      currentSocket &&
      (currentSocket.readyState === WebSocket.OPEN || currentSocket.readyState === WebSocket.CONNECTING)
    ) {
      return;
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/chat/${sessionId}`;
    const ws = new WebSocket(wsUrl);
    socketRef.current = ws;
    setConnectionState('connecting');

    ws.onopen = () => {
      if (socketRef.current !== ws) return;
      reconnectAttemptsRef.current = 0;
      setConnectionState('connected');
    };

    ws.onmessage = (event) => {
      if (socketRef.current !== ws) return;
      try {
        const data = JSON.parse(event.data);

        if (data.type === 'message') {
          if (data.sender === 'operator') {
            setOperatorOnline(true);
            handlersRef.current.onOperatorConnected?.();
          }
          addMessage({
            id: data.id || Math.random().toString(),
            sender: data.sender,
            message: data.message,
            media_url: data.media_url,
            created_at: data.timestamp || new Date().toISOString(),
            status: 'delivered',
          });
        } else if (data.type === 'system') {
          if (data.status === 'claimed') {
            setOperatorOnline(true);
            handlersRef.current.onOperatorConnected?.();
          } else if (data.status === 'expired') {
            expiredRef.current = true;
            setConnectionState('expired');
            handlersRef.current.onExpired?.();
          } else if (data.status === 'rate_limit') {
            triggerCooldown(data.retry_after || 5);
          }
          if (data.message) {
            addMessage({
              id: Math.random().toString(),
              sender: 'system',
              message: data.message,
              created_at: new Date().toISOString(),
            });
          }
        }
      } catch (err) {
        console.error('[WebSocket] Parse error:', err);
      }
    };

    ws.onclose = () => {
      if (socketRef.current !== ws || expiredRef.current || !shouldReconnectRef.current) return;
      socketRef.current = null;

      if (reconnectAttemptsRef.current < MAX_RECONNECT) {
        reconnectAttemptsRef.current += 1;
        setConnectionState('reconnecting');
        reconnectTimerRef.current = setTimeout(connect, RECONNECT_DELAY);
      } else {
        setConnectionState('failed');
      }
    };

    ws.onerror = () => {
      if (socketRef.current !== ws) return;
      setConnectionState('error');
    };
  }, [sessionId, addMessage, triggerCooldown]);

  useEffect(() => {
    expiredRef.current = false;
    shouldReconnectRef.current = true;
    reconnectAttemptsRef.current = 0;
    setMessages([]);
    setOperatorOnline(false);
    connect();
    return () => {
      shouldReconnectRef.current = false;
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
      const ws = socketRef.current;
      socketRef.current = null;
      if (ws) {
        ws.onclose = null;
        ws.onerror = null;
        if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
          ws.close();
        }
      }
      if (cooldownTimerRef.current) {
        clearInterval(cooldownTimerRef.current);
        cooldownTimerRef.current = null;
      }
    };
  }, [connect]);

  const sendMessage = useCallback((text, mediaUrl = null) => {
    if (!socketRef.current || socketRef.current.readyState !== WebSocket.OPEN) return false;
    if (isCooldown) return false;
    if (!text?.trim() && !mediaUrl) return false;

    const timestamp = new Date().toISOString();
    const payload = { type: 'message', message: text?.trim() || '', ...(mediaUrl && { media_url: mediaUrl }) };

    addMessage({
      id: Math.random().toString(),
      sender: 'client',
      message: text?.trim() || '',
      media_url: mediaUrl,
      created_at: timestamp,
      status: 'sent',
    });

    socketRef.current.send(JSON.stringify(payload));
    triggerCooldown(1);
    return true;
  }, [isCooldown, addMessage, triggerCooldown]);

  return {
    messages,
    connectionState,
    operatorOnline,
    isCooldown,
    cooldownSec,
    sendMessage,
    triggerCooldown,
  };
}
