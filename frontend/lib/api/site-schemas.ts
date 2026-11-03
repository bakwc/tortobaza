import { z } from "zod";

import { ResponsiveImageSchema } from "./types";

export const DeliveryScheduleTierSchema = z.enum([
  "all_day",
  "same_day",
  "next_day",
  "plus_2",
  "plus_3",
]);

export const SiteCategoryImageSchema = z.object({
  preview: ResponsiveImageSchema.nullable(),
});

export const SiteCategorySchema = z.object({
  id: z.number(),
  slug: z.string(),
  name_en: z.string(),
  name_ka: z.string(),
  name_ru: z.string(),
  page_slug_en: z.string(),
  page_slug_ka: z.string(),
  page_slug_ru: z.string(),
  page_heading_en: z.string(),
  page_heading_ka: z.string(),
  page_heading_ru: z.string(),
  page_description_en: z.string(),
  page_description_ka: z.string(),
  page_description_ru: z.string(),
  seo_title_en: z.string(),
  seo_title_ka: z.string(),
  seo_title_ru: z.string(),
  seo_description_en: z.string(),
  seo_description_ka: z.string(),
  seo_description_ru: z.string(),
  image: SiteCategoryImageSchema.nullable(),
  position: z.number(),
  is_active: z.boolean(),
  delivery_schedule_tier: DeliveryScheduleTierSchema,
  updated_at: z.string(),
});

export const SiteCategoryLandingSchema = z.object({
  id: z.number(),
  slug: z.string(),
  source: z.number(),
  source_name: z.string(),
  page_slug_en: z.string(),
  page_slug_ka: z.string(),
  page_slug_ru: z.string(),
  page_heading_en: z.string(),
  page_heading_ka: z.string(),
  page_heading_ru: z.string(),
  page_description_en: z.string(),
  page_description_ka: z.string(),
  page_description_ru: z.string(),
  seo_title_en: z.string(),
  seo_title_ka: z.string(),
  seo_title_ru: z.string(),
  seo_description_en: z.string(),
  seo_description_ka: z.string(),
  seo_description_ru: z.string(),
  image: SiteCategoryImageSchema.nullable(),
  is_active: z.boolean(),
  updated_at: z.string(),
});

export const SiteCroppedImageSchema = z.object({
  original: ResponsiveImageSchema,
  cropped: ResponsiveImageSchema,
  width: z.number(),
  height: z.number(),
  crop_left: z.number().nullable(),
  crop_top: z.number().nullable(),
  crop_size: z.number().nullable(),
});

export const SiteOptionSchema = z.object({
  id: z.number(),
  name_en: z.string(),
  name_ka: z.string(),
  name_ru: z.string(),
  price_delta: z.string(),
  weight_kg: z.string().nullable(),
  position: z.number(),
  is_active: z.boolean(),
  crop_left: z.number().nullable(),
  crop_top: z.number().nullable(),
  crop_size: z.number().nullable(),
  image: SiteCroppedImageSchema.nullable(),
});

export const SiteOptionGroupSchema = z.object({
  id: z.number(),
  slug: z.string(),
  name_en: z.string(),
  name_ka: z.string(),
  name_ru: z.string(),
  selection_type: z.enum(["single", "multi"]),
  is_required_default: z.boolean(),
  min_selections: z.number(),
  max_selections: z.number().nullable(),
  options: z.array(SiteOptionSchema),
});

export const SiteProductImageSchema = z.object({
  id: z.number(),
  position: z.number(),
  alt_en: z.string(),
  alt_ka: z.string(),
  alt_ru: z.string(),
  crop_left: z.number().nullable(),
  crop_top: z.number().nullable(),
  crop_size: z.number().nullable(),
  image: SiteCroppedImageSchema,
});

export const SiteProductOptionGroupSchema = z.object({
  option_group: z.number(),
  option_group_name: z.string(),
  position: z.number(),
  is_required: z.boolean().nullable(),
});

export const SiteProductListItemSchema = z.object({
  id: z.number(),
  slug: z.string(),
  name_en: z.string(),
  name_ka: z.string(),
  name_ru: z.string(),
  base_price: z.string(),
  category: z.number(),
  category_name: z.string(),
  position: z.number(),
  is_active: z.boolean(),
  primary_image: ResponsiveImageSchema.nullable(),
});

export const SiteProductSchema = z.object({
  id: z.number(),
  slug: z.string(),
  name_en: z.string(),
  name_ka: z.string(),
  name_ru: z.string(),
  description_en: z.string(),
  description_ka: z.string(),
  description_ru: z.string(),
  base_price: z.string(),
  category: z.number(),
  category_name: z.string(),
  delivery_schedule_tier: DeliveryScheduleTierSchema.nullable(),
  tech_card: z.number().nullable(),
  tech_card_name: z.string().nullable(),
  position: z.number(),
  is_active: z.boolean(),
  created_at: z.string(),
  option_groups: z.array(SiteProductOptionGroupSchema),
  images: z.array(SiteProductImageSchema),
});

export const SiteTechCardChoiceSchema = z.object({
  id: z.number(),
  name: z.string(),
});

export type SiteCategory = z.infer<typeof SiteCategorySchema>;
export type SiteCategoryLanding = z.infer<typeof SiteCategoryLandingSchema>;
export type SiteOptionGroup = z.infer<typeof SiteOptionGroupSchema>;
export type SiteOption = z.infer<typeof SiteOptionSchema>;
export type SiteProductListItem = z.infer<typeof SiteProductListItemSchema>;
export type SiteProduct = z.infer<typeof SiteProductSchema>;
export type SiteProductImage = z.infer<typeof SiteProductImageSchema>;
export type SiteCroppedImage = z.infer<typeof SiteCroppedImageSchema>;
export type SiteTechCardChoice = z.infer<typeof SiteTechCardChoiceSchema>;
export type DeliveryScheduleTier = z.infer<typeof DeliveryScheduleTierSchema>;

export type SiteCategoryBody = Omit<SiteCategory, "id" | "image" | "updated_at">;
export type SiteCategoryLandingBody = Omit<
  SiteCategoryLanding,
  "id" | "source_name" | "image" | "updated_at"
>;
export type SiteOptionGroupBody = Omit<SiteOptionGroup, "id" | "options"> & {
  options: Array<
    Omit<SiteOption, "id" | "image"> & {
      id?: number | null;
    }
  >;
};
export type SiteProductBody = Omit<
  SiteProduct,
  "id" | "category_name" | "tech_card_name" | "created_at" | "images" | "option_groups"
> & {
  option_groups: Array<{
    option_group: number;
    position: number;
    is_required: boolean | null;
  }>;
};
