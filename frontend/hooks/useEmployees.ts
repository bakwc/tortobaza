"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { currentUserQueryKey } from "@/hooks/useAuth";
import { api } from "@/lib/api";
import type { EmployeeBody } from "@/lib/api/types";

export function useEmployees() {
  const qc = useQueryClient();
  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["employees"] });
    qc.invalidateQueries({ queryKey: currentUserQueryKey });
  };
  const list = useQuery({ queryKey: ["employees"], queryFn: () => api.employees.list() });
  const save = useMutation({
    mutationFn: ({ id, body }: { id: number | null; body: EmployeeBody }) =>
      id === null ? api.employees.create(body) : api.employees.update(id, body),
    onSuccess: invalidate,
  });
  return { list, save };
}
