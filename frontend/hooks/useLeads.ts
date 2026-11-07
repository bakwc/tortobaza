"use client";

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Resource } from "@/lib/api/endpoints";
import type { SocialMessageKind } from "@/lib/api/types";

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

export function socialMessagesQueryKey(
  kind: SocialMessageKind,
  network: string,
  channel: number | null,
  vertical: string,
  q: string,
  page: number,
) {
  return ["leads", "messages", kind, network, channel, vertical, q, page] as const;
}

export function useSocialMessages(
  kind: SocialMessageKind,
  network: string,
  channel: number | null,
  vertical: string,
  q: string,
  page: number,
) {
  return useQuery({
    queryKey: socialMessagesQueryKey(kind, network, channel, vertical, q, page),
    queryFn: ({ signal }) => api.socialMessages(kind, network, channel, vertical, q, page, signal),
    placeholderData: keepPreviousData,
  });
}

export function useSocialChannels() {
  return useResource(["leads", "channels"], api.socialChannels);
}

export function useSocialVerticals() {
  return useResource(["leads", "verticals"], api.socialVerticals);
}

export function useSocialSearchQueries() {
  return useResource(["leads", "search-queries"], api.socialSearchQueries);
}

export function useSocialKeywords(verticalId: number | null) {
  const qc = useQueryClient();
  const key = ["leads", "keywords", verticalId] as const;
  const list = useQuery({
    queryKey: key,
    queryFn: () => api.socialKeywords.list(verticalId as number),
    enabled: verticalId !== null,
  });
  const save = useMutation({
    mutationFn: ({ id, body }: { id: number | null; body: Parameters<typeof api.socialKeywords.create>[0] }) =>
      id === null ? api.socialKeywords.create(body) : api.socialKeywords.update(id, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: key }),
  });
  const remove = useMutation({
    mutationFn: (id: number) => api.socialKeywords.remove(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: key }),
  });
  return { list, save, remove };
}
