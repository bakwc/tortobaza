"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Resource } from "@/lib/api/endpoints";
import type { ComponentRefBody } from "@/lib/api/types";

const STOCK_KEYS = [["menu"], ["inventory"]] as const;

function useInvalidateStock() {
  const qc = useQueryClient();
  return () => {
    for (const key of STOCK_KEYS) {
      qc.invalidateQueries({ queryKey: key });
    }
  };
}

function useResource<T, B>(key: readonly string[], resource: Resource<T, B>) {
  const invalidate = useInvalidateStock();
  const list = useQuery<T[]>({ queryKey: key, queryFn: () => resource.list() });
  const save = useMutation({
    mutationFn: ({ id, body }: { id: number | null; body: B }) =>
      id === null ? resource.create(body) : resource.update(id, body),
    onSuccess: invalidate,
  });
  const remove = useMutation({
    mutationFn: (id: number) => resource.remove(id),
    onSuccess: invalidate,
  });
  return { list, save, remove };
}

export function useIngredientCategories() {
  return useResource(["menu", "ingredient-categories"], api.menuIngredientCategories);
}

export function useIngredients() {
  return useResource(["menu", "ingredients"], api.menuIngredients);
}

export function useSemiProducts() {
  return useResource(["menu", "semi-products"], api.menuSemiProducts);
}

export function useModifierGroups() {
  return useResource(["menu", "modifier-groups"], api.menuModifierGroups);
}

export function useTechCardCategories() {
  return useResource(["menu", "tech-card-categories"], api.menuTechCardCategories);
}

export function useTechCards() {
  return useResource(["menu", "tech-cards"], api.menuTechCards);
}

export function useSuppliers() {
  return useResource(["inventory", "suppliers"], api.inventorySuppliers);
}

export function useSupplies() {
  return useResource(["inventory", "supplies"], api.inventorySupplies);
}

export function useProductions() {
  return useResource(["inventory", "productions"], api.inventoryProductions);
}

export function useWriteOffReasons() {
  return useResource(["inventory", "write-off-reasons"], api.inventoryWriteOffReasons);
}

export function useWriteOffs() {
  return useResource(["inventory", "write-offs"], api.inventoryWriteOffs);
}

export function useInventoryCounts() {
  return useResource(["inventory", "inventory-counts"], api.inventoryCounts);
}

export function useCloseInventoryCount() {
  const invalidate = useInvalidateStock();
  return useMutation({
    mutationFn: (id: number) => api.closeInventoryCount(id),
    onSuccess: invalidate,
  });
}

export function useStockLevels(date: string | null) {
  return useQuery({
    queryKey: ["inventory", "stock", date],
    queryFn: () => api.getStock(date),
  });
}

export function useStockMovements(component: ComponentRefBody | null) {
  return useQuery({
    queryKey: ["inventory", "movements", component?.ingredient ?? null, component?.semi_product ?? null],
    queryFn: () => api.getStockMovements(component as ComponentRefBody),
    enabled: component !== null,
  });
}

export function useSupplyTransactions(supplyId: number | null) {
  return useQuery({
    queryKey: ["inventory", "supply-transactions", supplyId],
    queryFn: () => api.getSupplyTransactions(supplyId),
  });
}

export function useMissingModifierLines() {
  return useQuery({
    queryKey: ["menu", "missing-modifier-lines"],
    queryFn: () => api.getMissingModifierLines(),
  });
}

export function useCatalogOptions() {
  return useQuery({
    queryKey: ["menu", "catalog-options"],
    queryFn: () => api.getCatalogOptions(),
  });
}

export function useTechCardCost(
  techCardId: number | null,
  weightKg: string | null,
  modifiers: { modifier: number; quantity: number }[],
  enabled: boolean,
) {
  return useQuery({
    queryKey: ["menu", "tech-card-cost", techCardId, weightKg, modifiers],
    queryFn: () => api.getTechCardCost(techCardId as number, weightKg, modifiers),
    enabled: enabled && techCardId !== null,
  });
}
