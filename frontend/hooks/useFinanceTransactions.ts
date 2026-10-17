"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type {
  FinanceAccount,
  FinanceTransactionSearchResult,
  FinanceTransactionWriteBody,
  FinanceTransactionsResponse,
} from "@/lib/api/types";
import type { FinancePeriod } from "@/hooks/useFinancePeriod";

export function useFinanceTransactions(period: FinancePeriod) {
  return useQuery<FinanceTransactionsResponse>({
    queryKey: ["finance-transactions", "month", period.month] as const,
    queryFn: () => api.getFinanceTransactionsByMonth(period.month),
    staleTime: 0,
  });
}

export function useFinanceAccounts(enabled: boolean) {
  return useQuery<FinanceAccount[]>({
    queryKey: ["finance-accounts"] as const,
    queryFn: () => api.getFinanceAccounts(),
    enabled,
  });
}

export function useFinanceTransactionSearch(q: string) {
  return useQuery<FinanceTransactionSearchResult[]>({
    queryKey: ["finance-transaction-search", q] as const,
    queryFn: () => api.searchFinanceTransactions(q),
    enabled: q !== "",
  });
}

export function useCreateFinanceTransaction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: FinanceTransactionWriteBody) => api.createFinanceTransaction(body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["finance-transactions"] });
    },
  });
}

export function useUpdateFinanceTransaction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: number; body: FinanceTransactionWriteBody }) =>
      api.updateFinanceTransaction(id, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["finance-transactions"] });
    },
  });
}

export function useDeleteFinanceTransaction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.deleteFinanceTransaction(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["finance-transactions"] });
    },
  });
}
