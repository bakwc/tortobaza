"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { RsInvoice } from "@/lib/api/types";

export function useInvoices(month: string) {
  return useQuery<RsInvoice[]>({
    queryKey: ["rsge", "invoices", month],
    queryFn: () => api.getRsgeInvoices(month),
  });
}

export function useDecideInvoice() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (
      input: { id: number; action: "confirm" } | { id: number; action: "reject"; refText: string },
    ) =>
      input.action === "confirm"
        ? api.confirmRsgeInvoice(input.id)
        : api.rejectRsgeInvoice(input.id, input.refText),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["rsge", "invoices"] });
    },
  });
}
