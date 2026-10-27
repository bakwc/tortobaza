"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { RsgePendingCount } from "@/lib/api/types";

export const rsgePendingCountQueryKey = ["rsge", "pending-count"] as const;

export function useRsgePendingCount(enabled: boolean) {
  return useQuery<RsgePendingCount>({
    queryKey: rsgePendingCountQueryKey,
    queryFn: () => api.getRsgePendingCount(),
    enabled,
  });
}
