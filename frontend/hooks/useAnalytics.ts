"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { AnalyticsClients, AnalyticsLoad, AnalyticsPulse } from "@/lib/api/types";

export function useAnalyticsPulse(month: string) {
  return useQuery<AnalyticsPulse>({
    queryKey: ["analytics-pulse", month] as const,
    queryFn: () => api.getAnalyticsPulse(month),
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
