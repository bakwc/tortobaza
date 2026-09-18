"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  currentUserQueryKey,
  isUnauthenticatedError,
} from "@/hooks/useAuth";
import { api } from "@/lib/api";
import type {
  CrmExpensesDay,
  CrmExpensesMonth,
  CrmMapOrderRange,
  CrmMapOrdersResponse,
  CrmMonthlyOrdersResponse,
  CrmOrder,
  CrmOrdersResponse,
  ResolveGoogleAddressResponse,
  UpdateCrmOrderBody,
} from "@/lib/api/types";

export const crmOrdersQueryKey = (date?: string) =>
  date ? (["crm-orders", date] as const) : (["crm-orders"] as const);

export const crmMonthlyOrdersQueryKey = (month: string) =>
  ["crm-orders", "month", month] as const;

export const crmMapOrdersQueryKey = (
  range: CrmMapOrderRange | null,
  date: string | null,
) => ["crm-orders", "map", range, date] as const;

export const crmExpensesQueryKey = (date?: string) =>
  date ? (["crm-expenses", date] as const) : (["crm-expenses"] as const);

export const crmMonthlyExpensesQueryKey = (month: string) =>
  ["crm-expenses", "month", month] as const;

export const crmOrderQueryKey = (id: number) => ["crm-order", id] as const;

const CRM_BOARD_REFETCH_INTERVAL_MS = 15_000;

export function useCrmOrders(date?: string) {
  return useQuery<CrmOrdersResponse>({
    queryKey: crmOrdersQueryKey(date),
    queryFn: () => api.getCrmOrders(date),
    staleTime: 0,
    refetchInterval: CRM_BOARD_REFETCH_INTERVAL_MS,
    refetchOnWindowFocus: true,
  });
}

export function useCrmOrdersByMonth(month: string) {
  return useQuery<CrmMonthlyOrdersResponse>({
    queryKey: crmMonthlyOrdersQueryKey(month),
    queryFn: () => api.getCrmOrdersByMonth(month),
    staleTime: 0,
    refetchInterval: CRM_BOARD_REFETCH_INTERVAL_MS,
    refetchOnWindowFocus: true,
  });
}

export function useCrmMapOrders(range: CrmMapOrderRange | null, date: string | null) {
  return useQuery<CrmMapOrdersResponse>({
    queryKey: crmMapOrdersQueryKey(range, date),
    queryFn: () => api.getCrmMapOrders(range, date),
    staleTime: 0,
    refetchInterval: CRM_BOARD_REFETCH_INTERVAL_MS,
    refetchOnWindowFocus: true,
  });
}

export function useCrmExpenses(date: string | undefined, enabled: boolean) {
  return useQuery<CrmExpensesDay>({
    queryKey: crmExpensesQueryKey(date),
    queryFn: () => api.getCrmExpenses(date),
    enabled,
    staleTime: 0,
    refetchInterval: CRM_BOARD_REFETCH_INTERVAL_MS,
    refetchOnWindowFocus: true,
  });
}

export function useCrmExpensesByMonth(month: string, enabled: boolean) {
  return useQuery<CrmExpensesMonth>({
    queryKey: crmMonthlyExpensesQueryKey(month),
    queryFn: () => api.getCrmExpensesByMonth(month),
    enabled,
    staleTime: 0,
    refetchInterval: CRM_BOARD_REFETCH_INTERVAL_MS,
    refetchOnWindowFocus: true,
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
    onError: (error) => {
      if (isUnauthenticatedError(error)) {
        qc.setQueryData(currentUserQueryKey, null);
      }
    },
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

export function useDeleteCrmOrder() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.deleteCrmOrder(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["crm-orders"] });
    },
  });
}

export function useResolveYandexAddress() {
  return useMutation({
    mutationFn: (address: string) => api.resolveYandexAddress(address),
  });
}

export function useResolveGoogleAddress() {
  return useMutation({
    mutationFn: (address: string) => api.resolveGoogleAddress(address),
  });
}

export function useCrmClientOrderMap(token: string, enabled: boolean) {
  return useQuery<ResolveGoogleAddressResponse>({
    queryKey: ["crm-client-order-map", token],
    queryFn: () => api.getCrmClientOrderMap(token),
    enabled,
  });
}
