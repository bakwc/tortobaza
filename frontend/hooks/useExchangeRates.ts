"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { ExchangeRates } from "@/lib/api/types";

export function useExchangeRates() {
  return useQuery<ExchangeRates>({
    queryKey: ["exchange-rates"] as const,
    queryFn: () => api.getExchangeRates(),
    staleTime: 0,
  });
}
