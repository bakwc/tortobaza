"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { rsgePendingCountQueryKey } from "@/hooks/useRsgePendingCount";
import { api } from "@/lib/api";
import type { RsWaybill } from "@/lib/api/types";

export function useWaybills(month: string) {
  return useQuery<RsWaybill[]>({
    queryKey: ["rsge", "waybills", month],
    queryFn: () => api.getRsgeWaybills(month),
  });
}

export function useDecideWaybill() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, action }: { id: number; action: "confirm" | "reject" }) =>
      action === "confirm" ? api.confirmRsgeWaybill(id) : api.rejectRsgeWaybill(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["rsge", "waybills"] });
      qc.invalidateQueries({ queryKey: rsgePendingCountQueryKey });
    },
  });
}
