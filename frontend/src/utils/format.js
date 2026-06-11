export function formatPrice(price) {
  if (price == null) return 'Kelishilgan narx';
  return `${Number(price).toLocaleString('uz-UZ')} so'm/oy`;
}

export function formatTime(isoString) {
  if (!isoString) return '';
  try {
    return new Date(normalizeIsoTime(isoString)).toLocaleTimeString('uz-UZ', {
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return '';
  }
}

export function formatDateTime(isoString) {
  if (!isoString) return '';
  try {
    return new Date(normalizeIsoTime(isoString)).toLocaleString('uz-UZ', {
      day: '2-digit',
      month: 'long',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return '';
  }
}

export function formatPhone(digits) {
  const clean = digits.replace(/\D/g, '').slice(0, 9);
  return `+998${clean}`;
}

function normalizeIsoTime(value) {
  if (typeof value !== 'string') return value;
  const trimmed = value.trim();
  if (!trimmed) return trimmed;
  if (/[zZ]$|[+-]\d{2}:?\d{2}$/.test(trimmed)) return trimmed;
  return `${trimmed}Z`;
}
