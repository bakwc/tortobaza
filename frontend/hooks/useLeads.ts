"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Resource } from "@/lib/api/endpoints";
import type { TelegramMessageKind } from "@/lib/api/types";

function useResource<T, B>(key: readonly string[], resource: Resource<T, B>) {
  const qc = useQueryClient();
  const list = useQuery<T[]>({ queryKey: key, queryFn: () => resource.list() });
  const save = useMutation({
    mutationFn: ({ id, body }: { id: number | null; body: B }) =>
      id === null ? resource.create(body) : resource.update(id, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: key }),
  });
  const remove = useMutation({
    mutationFn: (id: number) => resource.remove(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: key }),
  });
  return { list, save, remove };
}

export function useTelegramMessages(kind: TelegramMessageKind, q: string, page: number) {
  return useQuery({
    queryKey: ["leads", "messages", kind, q, page],
    queryFn: () => api.telegramMessages(kind, q, page),
  });
}

export function useTelegramChannels() {
  return useResource(["leads", "channels"], api.telegramChannels);
}

export function useTelegramKeywords() {
  return useResource(["leads", "keywords"], api.telegramKeywords);
}
