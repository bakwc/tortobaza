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
};

export function useAuditEvents(query: AuditEventsQuery) {
  return useQuery<AuditEventsResponse>({
    queryKey: ["audit-events", query] as const,
    queryFn: () => api.getAuditEvents(query),
  });
}
