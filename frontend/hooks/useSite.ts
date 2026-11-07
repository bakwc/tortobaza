"use client";

import { useSearchParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { usePathname, useRouter } from "@/i18n/navigation";
import { api } from "@/lib/api";
import type {
  SiteCategoryBody,
  SiteCategoryLandingBody,
  SiteOptionGroupBody,
  SiteProductBody,
} from "@/lib/api/site-schemas";

export function useShowHidden(): boolean {
  const searchParams = useSearchParams();
  return searchParams.get("show_hidden") === "1";
}

export function useSetShowHidden(): (value: boolean) => void {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  return (value: boolean) => {
    const params = new URLSearchParams(searchParams.toString());
    if (value) params.set("show_hidden", "1");
    else params.delete("show_hidden");
    const query = params.toString();
    router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false });
  };
}

function useInvalidateSite() {
  const client = useQueryClient();
  return () => client.invalidateQueries({ queryKey: ["site"] });
}

function useSiteResource<T, B>(
  key: readonly string[],
  resource: {
    list: () => Promise<T[]>;
    get: (id: number) => Promise<T>;
    create: (body: B) => Promise<T>;
    update: (id: number, body: B) => Promise<T>;
    remove: (id: number) => Promise<void>;
  },
) {
  const invalidate = useInvalidateSite();
  const list = useQuery({ queryKey: key, queryFn: () => resource.list() });
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

export function useSiteCategories() {
  return useSiteResource(["site", "categories"], api.siteCategories);
}

export function useSiteCategoryLandings() {
  return useSiteResource(["site", "category-landings"], api.siteCategoryLandings);
}

export function useSiteOptionGroups() {
  return useSiteResource(["site", "option-groups"], api.siteOptionGroups);
}

export function useSiteProducts(filters: { category?: number; search?: string }) {
  const invalidate = useInvalidateSite();
  const list = useQuery({
    queryKey: ["site", "products", filters.category ?? null, filters.search ?? ""],
    queryFn: () => api.listSiteProducts(filters),
  });
  const save = useMutation({
    mutationFn: ({ id, body }: { id: number | null; body: SiteProductBody }) =>
      id === null ? api.createSiteProduct(body) : api.updateSiteProduct(id, body),
    onSuccess: invalidate,
  });
  const remove = useMutation({
    mutationFn: ({ id, confirm }: { id: number; confirm: boolean }) =>
      api.deleteSiteProduct(id, confirm),
    onSuccess: invalidate,
  });
  return { list, save, remove };
}

export function useSiteProductDetail(id: number | null) {
  return useQuery({
    queryKey: ["site", "products", "detail", id],
    queryFn: () => api.getSiteProduct(id as number),
    enabled: id !== null,
  });
}

export function useSiteTechCards() {
  return useQuery({
    queryKey: ["site", "tech-cards"],
    queryFn: () => api.listSiteTechCards(),
  });
}

export function useSiteCategoryImageUpload() {
  const invalidate = useInvalidateSite();
  return useMutation({
    mutationFn: ({ id, file }: { id: number; file: File }) => api.uploadSiteCategoryImage(id, file),
    onSuccess: invalidate,
  });
}

export function useSiteCategoryImageDelete() {
  const invalidate = useInvalidateSite();
  return useMutation({
    mutationFn: (id: number) => api.deleteSiteCategoryImage(id),
    onSuccess: invalidate,
  });
}

export function useSiteCategoryLandingImageUpload() {
  const invalidate = useInvalidateSite();
  return useMutation({
    mutationFn: ({ id, file }: { id: number; file: File }) => api.uploadSiteCategoryLandingImage(id, file),
    onSuccess: invalidate,
  });
}

export function useSiteCategoryLandingImageDelete() {
  const invalidate = useInvalidateSite();
  return useMutation({
    mutationFn: (id: number) => api.deleteSiteCategoryLandingImage(id),
    onSuccess: invalidate,
  });
}

export function useSiteOptionImageUpload() {
  const invalidate = useInvalidateSite();
  return useMutation({
    mutationFn: ({ id, file }: { id: number; file: File }) => api.uploadSiteOptionImage(id, file),
    onSuccess: invalidate,
  });
}

export function useSiteOptionImageDelete() {
  const invalidate = useInvalidateSite();
  return useMutation({
    mutationFn: (id: number) => api.deleteSiteOptionImage(id),
    onSuccess: invalidate,
  });
}

export function useSiteProductImages(productId: number | null) {
  const invalidate = useInvalidateSite();
  const upload = useMutation({
    mutationFn: ({
      targetId,
      file,
      fields,
    }: {
      targetId: number;
      file: File;
      fields: {
        alt_en?: string;
        alt_ka?: string;
        alt_ru?: string;
        crop_left?: number | null;
        crop_top?: number | null;
        crop_size?: number | null;
      };
    }) => api.uploadSiteProductImage(targetId, file, fields),
    onSuccess: invalidate,
  });
  const patch = useMutation({
    mutationFn: ({
      imageId,
      body,
    }: {
      imageId: number;
      body: {
        position?: number;
        alt_en?: string;
        alt_ka?: string;
        alt_ru?: string;
        crop_left?: number | null;
        crop_top?: number | null;
        crop_size?: number | null;
      };
    }) => api.patchSiteProductImage(productId as number, imageId, body),
    onSuccess: invalidate,
  });
  const remove = useMutation({
    mutationFn: (imageId: number) => api.deleteSiteProductImage(productId as number, imageId),
    onSuccess: invalidate,
  });
  const reorder = useMutation({
    mutationFn: (ids: number[]) => api.reorderSiteProductImages(productId as number, ids),
    onSuccess: invalidate,
  });
  return { upload, patch, remove, reorder };
}
