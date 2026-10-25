"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { AnalyticsClients, AnalyticsLoad, AnalyticsOverview } from "@/lib/api/types";

export function useAnalyticsOverview() {
  return useQuery<AnalyticsOverview>({
    queryKey: ["analytics-overview"] as const,
    queryFn: () => api.getAnalyticsOverview(),
    staleTime: 0,
  });
}

export function useAnalyticsLoad(month: string) {
  return useQuery<AnalyticsLoad>({
    queryKey: ["analytics-load", month] as const,
    queryFn: () => api.getAnalyticsLoad(month),
    staleTime: 0,
  });
}

export function useAnalyticsClients() {
  return useQuery<AnalyticsClients>({
    queryKey: ["analytics-clients"] as const,
    queryFn: () => api.getAnalyticsClients(),
    staleTime: 0,
  });
}
