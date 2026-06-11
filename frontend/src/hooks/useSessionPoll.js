import { useState, useEffect, useRef } from 'react';
import { fetchSession } from '../utils/api';

const STATES = [
  { key: 'creating', label: 'Sessiya yaratilmoqda', minMs: 0 },
  { key: 'topic', label: 'Topic yaratilmoqda', minMs: 1500 },
  { key: 'searching', label: 'Operator qidirilmoqda', minMs: 3000 },
  { key: 'connected', label: 'Operatorga ulandi', minMs: 4500 },
];

export default function useSessionPoll(sessionId, onReady) {
  const [currentState, setCurrentState] = useState(STATES[0]);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState(null);
  const readyCalledRef = useRef(false);
  const startTimeRef = useRef(Date.now());

  useEffect(() => {
    if (!sessionId) return;

    startTimeRef.current = Date.now();
    readyCalledRef.current = false;

    const stateTimer = setInterval(() => {
      const elapsed = Date.now() - startTimeRef.current;
      const state = [...STATES].reverse().find((s) => elapsed >= s.minMs) || STATES[0];
      setCurrentState(state);
      setProgress(Math.min(95, (elapsed / 6000) * 100));
    }, 300);

    const poll = async () => {
      try {
        const data = await fetchSession(sessionId);
        if (!data) {
          setError('Sessiya topilmadi');
          return;
        }

        if (data.is_active && data.topic_status === 'active' && !readyCalledRef.current) {
          readyCalledRef.current = true;
          setCurrentState(STATES[3]);
          setProgress(100);
          setTimeout(() => onReady?.(data), 800);
        }
      } catch {
        setError('Ulanishda xatolik yuz berdi');
      }
    };

    poll();
    const pollInterval = setInterval(poll, 1500);

    const timeout = setTimeout(() => {
      if (!readyCalledRef.current) {
        fetchSession(sessionId).then((data) => {
          if (data?.is_active) {
            readyCalledRef.current = true;
            onReady?.(data);
          } else {
            setError('Sessiya yaratish vaqti tugadi. Qayta urinib ko\'ring.');
          }
        });
      }
    }, 30000);

    return () => {
      clearInterval(stateTimer);
      clearInterval(pollInterval);
      clearTimeout(timeout);
    };
  }, [sessionId, onReady]);

  return { currentState, progress, error };
}
