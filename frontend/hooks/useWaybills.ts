"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { RsWaybill } from "@/lib/api/types";

export function useWaybills(month: string) {
  return useQuery<RsWaybill[]>({
    queryKey: ["rsge", "waybills", month],
    queryFn: () => api.getRsgeWaybills(month),
  });
}
