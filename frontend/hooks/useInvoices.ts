"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { RsInvoice } from "@/lib/api/types";

export function useInvoices(month: string) {
  return useQuery<RsInvoice[]>({
    queryKey: ["rsge", "invoices", month],
    queryFn: () => api.getRsgeInvoices(month),
  });
}
