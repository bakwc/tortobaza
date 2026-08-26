"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type {
  CrmMonthlyOrdersResponse,
  CrmOrder,
  CrmOrdersResponse,
  UpdateCrmOrderBody,
} from "@/lib/api/types";

export const crmOrdersQueryKey = (date?: string) =>
  date ? (["crm-orders", date] as const) : (["crm-orders"] as const);

export const crmMonthlyOrdersQueryKey = (month: string) =>
  ["crm-orders", "month", month] as const;

export const crmOrderQueryKey = (id: number) => ["crm-order", id] as const;

export function useCrmOrders(date?: string) {
  return useQuery<CrmOrdersResponse>({
    queryKey: crmOrdersQueryKey(date),
    queryFn: () => api.getCrmOrders(date),
  });
}

export function useCrmOrdersByMonth(month: string) {
  return useQuery<CrmMonthlyOrdersResponse>({
    queryKey: crmMonthlyOrdersQueryKey(month),
    queryFn: () => api.getCrmOrdersByMonth(month),
  });
}

export function useCrmOrder(id: number) {
  return useQuery<CrmOrder>({
    queryKey: crmOrderQueryKey(id),
    queryFn: () => api.getCrmOrder(id),
    enabled: Number.isFinite(id),
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

export function useCreateCrmOrder() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: FormData) => api.createCrmOrder(body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["crm-orders"] });
    },
  });
}

export function useUpdateCrmOrder() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: number; body: FormData }) =>
      api.updateCrmOrder(id, body),
    onSuccess: (_data, variables) => {
      qc.invalidateQueries({ queryKey: ["crm-orders"] });
      qc.invalidateQueries({ queryKey: crmOrderQueryKey(variables.id) });
    },
  });
}
