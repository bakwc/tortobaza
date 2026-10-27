"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { FinanceScope } from "@/lib/api/endpoints";
import { api } from "@/lib/api";
import type {
  FinanceAccount,
  FinanceTransactionSearchResult,
  FinanceTransactionWriteBody,
  FinanceTransactionsResponse,
} from "@/lib/api/types";
import type { FinancePeriod } from "@/hooks/useFinancePeriod";

export function useFinanceTransactions(period: FinancePeriod, scope: FinanceScope) {
  return useQuery<FinanceTransactionsResponse>({
    queryKey: ["finance-transactions", scope, "month", period.month] as const,
    queryFn: () => api.getFinanceTransactionsByMonth(period.month, scope),
    staleTime: 0,
  });
}

export function useFinanceTransactionsRange(start: string, end: string, scope: FinanceScope) {
  return useQuery<FinanceTransactionsResponse>({
    queryKey: ["finance-transactions", scope, "range", start, end] as const,
    queryFn: () => api.getFinanceTransactionsByRange(start, end, scope),
    staleTime: 0,
  });
}

export function useFinanceAccounts(enabled: boolean, scope: FinanceScope) {
  return useQuery<FinanceAccount[]>({
    queryKey: ["finance-accounts", scope] as const,
    queryFn: () => api.getFinanceAccounts(scope),
    enabled,
  });
}

export function useFinanceTransactionSearch(q: string, scope: FinanceScope) {
  return useQuery<FinanceTransactionSearchResult[]>({
    queryKey: ["finance-transaction-search", scope, q] as const,
    queryFn: () => api.searchFinanceTransactions(q, scope),
    enabled: q !== "",
  });
}

export function useCreateFinanceTransaction(scope: FinanceScope) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: FinanceTransactionWriteBody) => api.createFinanceTransaction(body, scope),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["finance-transactions", scope] });
    },
  });
}

export function useUpdateFinanceTransaction(scope: FinanceScope) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: number; body: FinanceTransactionWriteBody }) =>
      api.updateFinanceTransaction(id, body, scope),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["finance-transactions", scope] });
    },
  });
}

export function useDeleteFinanceTransaction(scope: FinanceScope) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.deleteFinanceTransaction(id, scope),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["finance-transactions", scope] });
    },
  });
}
