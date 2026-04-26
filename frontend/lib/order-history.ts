const STORAGE_KEY = "tortobaza:orders";

export type StoredOrder = {
  number: string;
  token: string;
  rememberedAt: string;
};

export function rememberOrder(orderNumber: string, lookupToken: string): void {
  if (typeof window === "undefined") return;
  const existing = listOrders();
  const filtered = existing.filter((o) => o.number !== orderNumber);
  const next: StoredOrder[] = [
    { number: orderNumber, token: lookupToken, rememberedAt: new Date().toISOString() },
    ...filtered,
  ].slice(0, 20);
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
}

export function listOrders(): StoredOrder[] {
  if (typeof window === "undefined") return [];
  const raw = window.localStorage.getItem(STORAGE_KEY);
  if (!raw) return [];
  try {
    return JSON.parse(raw) as StoredOrder[];
  } catch {
    return [];
  }
}

export function getOrderToken(orderNumber: string): string | null {
  return listOrders().find((o) => o.number === orderNumber)?.token ?? null;
}
