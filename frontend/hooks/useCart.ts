"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { AddCartItemBody, Cart, UpdateCartItemBody } from "@/lib/api/types";

export const cartQueryKey = ["cart"] as const;
export const fulfillmentOptionsQueryKey = ["fulfillment-options"] as const;

export function useCart(initialData?: Cart) {
  return useQuery<Cart>({
    queryKey: cartQueryKey,
    queryFn: () => api.getCart(),
    initialData,
  });
}

export function useAddCartItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: AddCartItemBody) => api.addCartItem(body),
    onSuccess: (data) => {
      qc.setQueryData(cartQueryKey, data);
      qc.invalidateQueries({ queryKey: fulfillmentOptionsQueryKey });
    },
  });
}

export function useUpdateCartItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: number; body: UpdateCartItemBody }) =>
      api.updateCartItem(id, body),
    onMutate: async ({ id, body }) => {
      await qc.cancelQueries({ queryKey: cartQueryKey });
      const previous = qc.getQueryData<Cart>(cartQueryKey);
      if (previous && body.quantity !== undefined) {
        const items = previous.items.map((item) =>
          item.id === id ? { ...item, quantity: body.quantity ?? item.quantity } : item,
        );
        qc.setQueryData<Cart>(cartQueryKey, { ...previous, items });
      }
      return { previous };
    },
    onError: (_err, _vars, ctx) => {
      if (ctx?.previous) qc.setQueryData(cartQueryKey, ctx.previous);
    },
    onSuccess: (data) => {
      qc.setQueryData(cartQueryKey, data);
      qc.invalidateQueries({ queryKey: fulfillmentOptionsQueryKey });
    },
  });
}

export function useRemoveCartItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.removeCartItem(id),
    onMutate: async (id) => {
      await qc.cancelQueries({ queryKey: cartQueryKey });
      const previous = qc.getQueryData<Cart>(cartQueryKey);
      if (previous) {
        const items = previous.items.filter((item) => item.id !== id);
        qc.setQueryData<Cart>(cartQueryKey, { ...previous, items });
      }
      return { previous };
    },
    onError: (_err, _vars, ctx) => {
      if (ctx?.previous) qc.setQueryData(cartQueryKey, ctx.previous);
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: cartQueryKey });
      qc.invalidateQueries({ queryKey: fulfillmentOptionsQueryKey });
    },
  });
}

export function useClearCart() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.clearCart(),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: cartQueryKey });
      qc.invalidateQueries({ queryKey: fulfillmentOptionsQueryKey });
    },
  });
}
