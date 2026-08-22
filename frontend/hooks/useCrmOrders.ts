"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { CrmOrdersResponse, UpdateCrmOrderBody } from "@/lib/api/types";

export const crmOrdersQueryKey = (date?: string) =>
  date ? (["crm-orders", date] as const) : (["crm-orders"] as const);

export function useCrmOrders(date?: string) {
  return useQuery<CrmOrdersResponse>({
    queryKey: crmOrdersQueryKey(date),
    queryFn: () => api.getCrmOrders(date),
  });
}

export function usePatchCrmOrder() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: number; body: UpdateCrmOrderBody }) =>
      api.patchCrmOrder(id, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["crm-orders"] });
    },
  });
}
