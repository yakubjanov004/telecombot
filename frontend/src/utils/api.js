import { getTariffsFromAssets, enrichTariff } from './tariffGroups';

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/+$/, '');

export function apiUrl(path) {
  return `${API_BASE_URL}${path}`;
}

export function mediaUrl(path) {
  if (!path || path.startsWith('http')) return path;
  return apiUrl(path.startsWith('/api/') ? path : `/api${path}`);
}

function normalizeName(name) {
  return (name || '').replace(/\u00a0/g, ' ').trim().toUpperCase();
}

async function responseError(res, fallback) {
  const err = await res.json().catch(() => ({}));
  if (Array.isArray(err.detail)) {
    const detail = err.detail
      .map((item) => `${item.loc?.slice(1).join('.') || 'field'}: ${item.msg}`)
      .join('; ');
    return new Error(detail || fallback);
  }
  return new Error(err.detail || fallback);
}

export async function fetchTariffs(type) {
  const assets = getTariffsFromAssets(type);
  const assetNames = new Set(assets.map((t) => normalizeName(t.name)));

  try {
    const res = await fetch(apiUrl(`/api/tariffs?type=${type}`));
    if (res.ok) {
      const apiData = await res.json();
      if (apiData.length > 0) {
        const merged = assets.map((a) => {
          const api = apiData.find((t) => normalizeName(t.name) === normalizeName(a.name));
          return api ? enrichTariff({ ...a, ...api }) : a;
        });
        apiData.forEach((api) => {
          if (!assetNames.has(normalizeName(api.name))) {
            merged.push(enrichTariff(api));
          }
        });
        return merged;
      }
    }
  } catch {
    /* API mavjud emas — assetsdan o'qiladi */
  }
  return assets;
}

export async function fetchSession(sessionId) {
  const res = await fetch(apiUrl(`/api/sessions/${sessionId}`));
  if (!res.ok) return null;
  return res.json();
}

export async function closeChatSession(sessionId) {
  const res = await fetch(apiUrl(`/api/sessions/${sessionId}/close`), { method: 'POST' });
  if (!res.ok) throw new Error('Chatni tugatishda xatolik yuz berdi');
  return res.json();
}

export async function submitInternetApplication(data) {
  const res = await fetch(apiUrl('/api/applications/internet'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    throw await responseError(res, 'Ariza topshirishda xatolik yuz berdi');
  }
  return res.json();
}

export async function submitMobileApplication(data) {
  const res = await fetch(apiUrl('/api/applications/mobile'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    throw await responseError(res, 'Ariza topshirishda xatolik yuz berdi');
  }
  return res.json();
}

export async function createSession(data) {
  const res = await fetch(apiUrl('/api/sessions'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error('Chat sessiyasi ochishda xatolik yuz berdi');
  return res.json();
}

export async function uploadChatImage(file) {
  const formData = new FormData();
  formData.append('file', file);
  const res = await fetch(apiUrl('/api/chat/upload'), { method: 'POST', body: formData });
  if (!res.ok) throw new Error('Rasm yuklashda xatolik yuz berdi');
  return res.json();
}
