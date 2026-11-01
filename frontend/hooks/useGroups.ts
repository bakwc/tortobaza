"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { AccessGroupBody } from "@/lib/api/types";

export function useGroups() {
  const qc = useQueryClient();
  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["groups"] });
    qc.invalidateQueries({ queryKey: ["employees"] });
  };
  const list = useQuery({ queryKey: ["groups"], queryFn: () => api.groups.list() });
  const permissions = useQuery({ queryKey: ["section-permissions"], queryFn: () => api.permissions() });
  const save = useMutation({
    mutationFn: ({ id, body }: { id: number | null; body: AccessGroupBody }) =>
      id === null ? api.groups.create(body) : api.groups.update(id, body),
    onSuccess: invalidate,
  });
  const remove = useMutation({
    mutationFn: (id: number) => api.groups.remove(id),
    onSuccess: invalidate,
  });
  return { list, permissions, save, remove };
}
