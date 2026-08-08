"use client";

import { useEffect } from "react";
import { getOrderToken } from "@/lib/order-history";
import { useRouter } from "@/i18n/navigation";

export function OrderTokenLookup({ orderNumber }: { orderNumber: string }) {
  const router = useRouter();

  useEffect(() => {
    const token = getOrderToken(orderNumber);
    if (token) {
      router.replace(`/orders/${orderNumber}?token=${token}`);
    }
  }, [orderNumber, router]);

  return null;
}
