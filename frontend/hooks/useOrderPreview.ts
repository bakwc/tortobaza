"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { FulfillmentType } from "@/lib/api/types";
import { useCart } from "@/hooks/useCart";

export function useOrderPreview(fulfillmentType: FulfillmentType, promoCode: string) {
  const { data: cart } = useCart();

  return useQuery({
    queryKey: ["order-preview", fulfillmentType, promoCode, cart?.subtotal],
    queryFn: () =>
      api.previewOrder({
        fulfillment_type: fulfillmentType,
        promo_code: promoCode || undefined,
      }),
    enabled: Boolean(cart && cart.items.length > 0),
  });
}
