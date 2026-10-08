"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { FinanceTransactionsResponse } from "@/lib/api/types";
import type { FinancePeriod } from "@/hooks/useFinancePeriod";

export function useFinanceTransactions(period: FinancePeriod) {
  return useQuery<FinanceTransactionsResponse>({
    queryKey:
      period.mode === "month"
        ? (["finance-transactions", "month", period.month] as const)
        : (["finance-transactions", "date", period.date] as const),
    queryFn: () =>
      period.mode === "month"
        ? api.getFinanceTransactionsByMonth(period.month)
        : api.getFinanceTransactions(period.date),
    staleTime: 0,
  });
}
