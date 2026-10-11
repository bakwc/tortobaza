"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { FinanceTransactionsResponse } from "@/lib/api/types";
import type { FinancePeriod } from "@/hooks/useFinancePeriod";

export function useFinanceTransactions(period: FinancePeriod) {
  return useQuery<FinanceTransactionsResponse>({
    queryKey: ["finance-transactions", "month", period.month] as const,
    queryFn: () => api.getFinanceTransactionsByMonth(period.month),
    staleTime: 0,
  });
}
