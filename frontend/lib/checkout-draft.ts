import type { FulfillmentType, OrderAddress, PaymentMethod } from "@/lib/api/types";

const STORAGE_KEY = "tortobaza:checkout-draft";

export type CheckoutDraft = {
  fulfillment_type: FulfillmentType;
  address: OrderAddress | null;
  pickup_location_id: number | null;
  timeslot_id: number | null;
  payment_method: PaymentMethod;
  customer_name: string;
  customer_phone: string;
  customer_email: string;
  comment: string;
  promo_code: string;
};

export const emptyDraft: CheckoutDraft = {
  fulfillment_type: "delivery",
  address: null,
  pickup_location_id: null,
  timeslot_id: null,
  payment_method: "card",
  customer_name: "",
  customer_phone: "",
  customer_email: "",
  comment: "",
  promo_code: "",
};

export function loadDraft(): CheckoutDraft {
  if (typeof window === "undefined") return emptyDraft;
  const raw = window.sessionStorage.getItem(STORAGE_KEY);
  if (!raw) return emptyDraft;
  try {
    const parsed = JSON.parse(raw) as Partial<CheckoutDraft>;
    return { ...emptyDraft, ...parsed };
  } catch {
    return emptyDraft;
  }
}

export function saveDraft(draft: CheckoutDraft): void {
  if (typeof window === "undefined") return;
  window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(draft));
}

export function clearDraft(): void {
  if (typeof window === "undefined") return;
  window.sessionStorage.removeItem(STORAGE_KEY);
}
