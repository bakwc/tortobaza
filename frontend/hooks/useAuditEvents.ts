"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { AuditEventsResponse } from "@/lib/api/types";

export type AuditEventsQuery = {
  page: number;
  start: string;
  end: string;
  app: string;
  q: string;
  model: string | null;
  objectId: string | null;
};

export function useAuditEvents(query: AuditEventsQuery, enabled: boolean) {
  return useQuery<AuditEventsResponse>({
    queryKey: ["audit-events", query] as const,
    queryFn: () => api.getAuditEvents(query),
    enabled,
  });
}
