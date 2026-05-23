import { z } from "zod";

export const CategorySchema = z.object({
  id: z.number(),
  slug: z.string(),
  name: z.string(),
  position: z.number(),
});

export const ResponsiveImageSchema = z.object({
  src: z.string(),
  srcset: z.string(),
});

export const ProductImageSchema = z.object({
  id: z.number(),
  image: ResponsiveImageSchema,
  alt: z.string().nullable().optional(),
  position: z.number(),
});

export const OptionSchema = z.object({
  id: z.number(),
  name: z.string(),
  price_delta: z.string(),
  position: z.number(),
  image: ResponsiveImageSchema.nullable().optional(),
});

export const OptionGroupSchema = z.object({
  id: z.number(),
  name: z.string(),
  slug: z.string(),
  selection_type: z.enum(["single", "multi"]),
  is_required: z.boolean(),
  position: z.number(),
  options: z.array(OptionSchema),
});

export const ProductListItemSchema = z.object({
  id: z.number(),
  slug: z.string(),
  name: z.string(),
  base_price: z.string(),
  primary_image: ResponsiveImageSchema.nullable(),
  category: CategorySchema,
});

export const ProductDetailSchema = z.object({
  id: z.number(),
  slug: z.string(),
  name: z.string(),
  description: z.string(),
  base_price: z.string(),
  category: CategorySchema,
  images: z.array(ProductImageSchema),
  option_groups: z.array(OptionGroupSchema),
});

export const ProductsPageSchema = z.object({
  count: z.number(),
  next: z.string().nullable(),
  previous: z.string().nullable(),
  results: z.array(ProductListItemSchema),
});

export const CartItemOptionSchema = z.object({
  id: z.number(),
  name: z.string(),
  price_delta: z.string(),
  group_id: z.number(),
  group_name: z.string(),
});

export const CartItemSchema = z.object({
  id: z.number(),
  product: z.object({
    id: z.number(),
    slug: z.string(),
    name: z.string(),
    base_price: z.string(),
    primary_image: ResponsiveImageSchema.nullable(),
  }),
  quantity: z.number(),
  comment: z.string(),
  options: z.array(CartItemOptionSchema),
  unit_price: z.string(),
  line_total: z.string(),
  added_at: z.string(),
});

export const CartSchema = z.object({
  token: z.string(),
  items: z.array(CartItemSchema),
  subtotal: z.string(),
  created_at: z.string(),
  updated_at: z.string(),
});

export const PickupLocationSchema = z.object({
  id: z.number(),
  name: z.string(),
  address: z.string(),
  lat: z.string().nullable().optional(),
  lng: z.string().nullable().optional(),
});

export const FulfillmentSlotSchema = z.object({
  start_time: z.string(),
  end_time: z.string(),
});

export const FulfillmentDateEntrySchema = z.object({
  date: z.string(),
  slots: z.array(FulfillmentSlotSchema),
});

export const FulfillmentOptionsSchema = z.object({
  timezone: z.string(),
  express_available: z.boolean(),
  dates: z.array(FulfillmentDateEntrySchema),
});

export const PromoValidationSchema = z.object({
  valid: z.boolean(),
  code: z.string(),
  discount_type: z.enum(["percent", "fixed"]),
  discount_value: z.string(),
  subtotal: z.string(),
  discount_total: z.string(),
  total: z.string(),
});

export const OrderPreviewSchema = z.object({
  fulfillment_type: z.enum(["delivery", "pickup"]),
  subtotal: z.string(),
  discount_total: z.string(),
  total: z.string(),
  promo_code: z.string().nullable(),
});

export const OrderItemOptionSchema = z.object({
  group_name: z.string(),
  option_name: z.string(),
  price_delta: z.string(),
});

export const OrderItemSchema = z.object({
  id: z.number(),
  product_name: z.string(),
  unit_price: z.string(),
  quantity: z.number(),
  comment: z.string(),
  line_total: z.string(),
  options: z.array(OrderItemOptionSchema),
});

export const OrderAddressSchema = z.object({
  street: z.string(),
  building: z.string(),
  apartment: z.string(),
  city: z.string(),
  postal_code: z.string(),
  notes: z.string(),
});

export const OrderSchema = z.object({
  number: z.string(),
  lookup_token: z.string(),
  fulfillment_type: z.enum(["delivery", "pickup"]),
  status: z.string(),
  payment_method: z.string(),
  payment_status: z.string(),
  customer_name: z.string(),
  customer_phone: z.string(),
  customer_email: z.string(),
  comment: z.string(),
  pickup_location: PickupLocationSchema.nullable(),
  delivery_address: OrderAddressSchema.nullable(),
  timeslot_start: z.string().nullable(),
  timeslot_end: z.string().nullable(),
  subtotal: z.string(),
  discount_total: z.string(),
  total: z.string(),
  items: z.array(OrderItemSchema),
  created_at: z.string(),
});

export type Category = z.infer<typeof CategorySchema>;
export type ProductImage = z.infer<typeof ProductImageSchema>;
export type Option = z.infer<typeof OptionSchema>;
export type OptionGroup = z.infer<typeof OptionGroupSchema>;
export type ProductListItem = z.infer<typeof ProductListItemSchema>;
export type ProductDetail = z.infer<typeof ProductDetailSchema>;
export type ProductsPage = z.infer<typeof ProductsPageSchema>;
export type CartItemOption = z.infer<typeof CartItemOptionSchema>;
export type CartItem = z.infer<typeof CartItemSchema>;
export type Cart = z.infer<typeof CartSchema>;
export type PickupLocation = z.infer<typeof PickupLocationSchema>;
export type FulfillmentOptions = z.infer<typeof FulfillmentOptionsSchema>;
export type PromoValidation = z.infer<typeof PromoValidationSchema>;
export type OrderPreview = z.infer<typeof OrderPreviewSchema>;
export type OrderItemOption = z.infer<typeof OrderItemOptionSchema>;
export type OrderItem = z.infer<typeof OrderItemSchema>;
export type OrderAddress = z.infer<typeof OrderAddressSchema>;
export type Order = z.infer<typeof OrderSchema>;

export type FulfillmentType = "delivery" | "pickup";
export type PaymentMethod = "card" | "cash" | "bank_transfer";

export type AddCartItemBody = {
  product_id: number;
  quantity: number;
  option_ids: number[];
  comment: string;
};

export type UpdateCartItemBody = {
  quantity?: number;
  comment?: string;
  option_ids?: number[];
};

export type CheckoutSchedule =
  | { mode: "express" }
  | { mode: "slot"; date: string; start_time: string; end_time: string };

export type PlaceOrderBody = {
  fulfillment_type: FulfillmentType;
  address?: OrderAddress;
  pickup_location_id?: number;
  schedule_mode: "express" | "slot";
  schedule_date?: string;
  schedule_start_time?: string;
  schedule_end_time?: string;
  payment_method: PaymentMethod;
  customer_name: string;
  customer_phone: string;
  customer_email: string;
  comment: string;
  promo_code?: string;
};

export type PreviewOrderBody = {
  fulfillment_type: FulfillmentType;
  promo_code?: string;
};
