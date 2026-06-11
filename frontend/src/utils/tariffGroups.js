import tariffsData from '@assets/tariffs.json';

const nameToGroup = Object.fromEntries(
  tariffsData.tariffs.map((t) => [normalizeName(t.name), t.group]),
);

const assetsByName = Object.fromEntries(
  tariffsData.tariffs.map((t) => [normalizeName(t.name), t]),
);

function normalizeName(name) {
  return (name || '').replace(/\u00a0/g, ' ').trim().toUpperCase();
}

export function getGroups(serviceType) {
  return tariffsData.groups[serviceType] || [];
}

export function getGroupById(serviceType, groupId) {
  return getGroups(serviceType).find((g) => g.id === groupId) || null;
}

export function resolveGroupId(tariff) {
  if (tariff.group) return tariff.group;
  return nameToGroup[normalizeName(tariff.name)] || null;
}

export function enrichTariff(tariff) {
  const asset = assetsByName[normalizeName(tariff.name)];
  if (!asset) {
    return { ...tariff, group: resolveGroupId(tariff) };
  }
  return {
    ...asset,
    ...tariff,
    group: tariff.group || asset.group,
    price: tariff.price ?? asset.price,
    speed: tariff.speed || asset.speed || '',
    minutes: tariff.minutes || asset.minutes || '',
    sms: tariff.sms || asset.sms || '',
    mb: tariff.mb || asset.mb || '',
    description: tariff.description || asset.description || '',
  };
}

export function groupTariffs(tariffs, serviceType) {
  const groups = getGroups(serviceType);
  const map = Object.fromEntries(groups.map((g) => [g.id, []]));

  tariffs.forEach((raw) => {
    const t = enrichTariff(raw);
    const groupId = resolveGroupId(t);
    if (groupId && map[groupId]) {
      map[groupId].push(t);
    }
  });

  return groups
    .map((g) => ({ ...g, tariffs: map[g.id] || [] }))
    .filter((g) => g.tariffs.length > 0);
}

export function getTariffsFromAssets(type) {
  return tariffsData.tariffs.filter((t) => t.service_type === type);
}

export function getMinPrice(tariffs) {
  const priced = tariffs.map((t) => t.price).filter((p) => p != null && p > 0);
  if (!priced.length) return null;
  return Math.min(...priced);
}
