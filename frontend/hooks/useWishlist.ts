"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { WishlistItemBody } from "@/lib/api/types";

const key = ["wishlist"] as const;

export function useWishlist() {
  const qc = useQueryClient();
  const list = useQuery({ queryKey: key, queryFn: () => api.wishlistItems.list() });
  const save = useMutation({
    mutationFn: ({ id, body }: { id: number | null; body: WishlistItemBody }) =>
      id === null ? api.wishlistItems.create(body) : api.wishlistItems.update(id, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: key }),
  });
  const remove = useMutation({
    mutationFn: (id: number) => api.wishlistItems.remove(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: key }),
  });
  return { list, save, remove };
}
