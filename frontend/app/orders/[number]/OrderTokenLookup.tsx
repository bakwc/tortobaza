"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { getOrderToken } from "@/lib/order-history";

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
