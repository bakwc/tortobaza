"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { IdeaBody } from "@/lib/api/types";

const key = ["ideas"] as const;

export function useIdeas() {
  const qc = useQueryClient();
  const list = useQuery({ queryKey: key, queryFn: () => api.ideas.list() });
  const save = useMutation({
    mutationFn: ({ id, body }: { id: number | null; body: IdeaBody }) =>
      id === null ? api.ideas.create(body) : api.ideas.update(id, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: key }),
  });
  const remove = useMutation({
    mutationFn: (id: number) => api.ideas.remove(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: key }),
  });
  return { list, save, remove };
}
