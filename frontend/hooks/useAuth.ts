"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { ApiError } from "@/lib/api/client";
import type { LoginBody, SessionUser } from "@/lib/api/types";

export const currentUserQueryKey = ["current-user"] as const;

export function isUnauthenticatedError(error: unknown): boolean {
  return error instanceof ApiError && (error.status === 401 || error.status === 403);
}

export function useCurrentUser() {
  return useQuery<SessionUser>({
    queryKey: currentUserQueryKey,
    queryFn: async () => {
      await api.ensureCsrf();
      return api.getCurrentUser();
    },
    staleTime: 60_000,
    refetchOnWindowFocus: true,
    retry: false,
  });
}

export function useLogin() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: LoginBody) => {
      await api.ensureCsrf();
      return api.login(body);
    },
    onSuccess: (user) => {
      qc.setQueryData(currentUserQueryKey, user);
    },
  });
}

export function useCan(code: string): boolean {
  const currentUser = useCurrentUser();
  const permissions = currentUser.data?.permissions ?? [];
  if (permissions.includes(code)) return true;
  if (code.startsWith("view_")) {
    const section = code.slice("view_".length);
    return permissions.includes(`edit_${section}`) || permissions.includes(`edit_own_${section}`);
  }
  return false;
}

export function useCanSeeOrderAddress(fulfillmentType: "delivery" | "pickup"): boolean {
  const canEditOrders = useCan("edit_orders");
  const canDelivery = useCan("view_order_delivery_address");
  const canPickup = useCan("view_order_pickup_address");
  if (canEditOrders) return true;
  if (fulfillmentType === "pickup") return canPickup;
  return canDelivery;
}

export function useCanSeeOrderContacts(fulfillmentType: "delivery" | "pickup"): boolean {
  const canEditOrders = useCan("edit_orders");
  const canDelivery = useCan("view_order_delivery_contacts");
  const canPickup = useCan("view_order_pickup_contacts");
  if (canEditOrders) return true;
  if (fulfillmentType === "pickup") return canPickup;
  return canDelivery;
}

export function useLogout() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.logout(),
    onSuccess: () => {
      qc.clear();
    },
  });
}
