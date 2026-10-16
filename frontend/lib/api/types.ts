import { z } from "zod";

export const ResponsiveImageSchema = z.object({
  src: z.string(),
  srcset: z.string(),
});

export const CategoryPageSlugsSchema = z.object({
  en: z.string(),
  ka: z.string(),
  ru: z.string(),
});

export const CategoryLandingSchema = z.object({
  id: z.number(),
  slug: z.string(),
  page_slug: z.string(),
  page_slugs: CategoryPageSlugsSchema,
  updated_at: z.string(),
});

export const CategorySchema = z.object({
  id: z.number(),
  slug: z.string(),
  page_slug: z.string(),
  name: z.string(),
  position: z.number(),
  delivery_schedule_tier: z.enum([
    "all_day",
    "same_day",
    "next_day",
    "plus_2",
    "plus_3",
  ]),
  page_slugs: CategoryPageSlugsSchema,
  updated_at: z.string(),
});

export const CategoryDetailSchema = CategorySchema.extend({
  source_page_slug: z.string(),
  page_heading: z.string(),
  page_description: z.string(),
  seo_title: z.string(),
  seo_description: z.string(),
  image: ResponsiveImageSchema.nullable(),
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
  min_selections: z.number(),
  max_selections: z.number().nullable(),
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
  dates: z.array(FulfillmentDateEntrySchema),
});

export const PromoValidationSchema = z.object({
  valid: z.boolean(),
  code: z.string(),
  discount_type: z.enum(["percent", "fixed"]),
  discount_value: z.string(),
  subtotal: z.string(),
  discount_total: z.string(),
  delivery_fee: z.string(),
  total: z.string(),
});

export const OrderPreviewSchema = z.object({
  fulfillment_type: z.enum(["delivery", "pickup"]),
  subtotal: z.string(),
  discount_total: z.string(),
  delivery_fee: z.string(),
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

export const LibertyPaymentEnabledSchema = z.object({
  enabled: z.boolean(),
});

export const StartPaymentResponseSchema = z.object({
  action_url: z.string(),
  fields: z.record(z.string(), z.string()),
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
  customer_instagram: z.string(),
  customer_telegram: z.string(),
  comment: z.string(),
  pickup_location: PickupLocationSchema.nullable(),
  delivery_address: OrderAddressSchema.nullable(),
  timeslot_start: z.string().nullable(),
  timeslot_end: z.string().nullable(),
  subtotal: z.string(),
  discount_total: z.string(),
  delivery_fee: z.string(),
  total: z.string(),
  items: z.array(OrderItemSchema),
  created_at: z.string(),
});

export const SessionUserSchema = z.object({
  id: z.number(),
  username: z.string(),
  first_name: z.string(),
  last_name: z.string(),
  is_staff: z.boolean(),
  is_finance_admin: z.boolean(),
});

export const AttendanceEventSchema = z.object({
  id: z.number(),
  user: z.number(),
  event_type: z.enum(["arrival", "departure"]),
  timestamp: z.string(),
});

export const AttendanceSummaryRowSchema = z.object({
  date: z.string(),
  arrival: z.string().nullable(),
  departure: z.string().nullable(),
  hours: z.string(),
  money: z.string(),
});

export const AttendanceSummarySchema = z.object({
  hourly_rate: z.string(),
  rows: z.array(AttendanceSummaryRowSchema),
  total_hours: z.string(),
  total_money: z.string(),
});

export const CrmOrderImageSchema = z.object({
  id: z.number(),
  image: ResponsiveImageSchema,
  position: z.number(),
});

export const MenuUnitSchema = z.enum(["g", "ml", "pcs"]);

export const CrmOrderItemModifierSchema = z.object({
  id: z.number(),
  modifier: z.number(),
  modifier_name: z.string(),
  group: z.number(),
  quantity: z.number(),
});

export const CrmOrderItemLineSchema = z.object({
  id: z.number(),
  ingredient: z.number().nullable(),
  semi_product: z.number().nullable(),
  name: z.string(),
  unit: MenuUnitSchema,
  quantity: z.string(),
});

export const CrmOrderItemSchema = z.object({
  id: z.number(),
  tech_card: z.number().nullable(),
  tech_card_name: z.string().nullable(),
  tech_card_kind: z.enum(["weighted", "piece"]).nullable(),
  name: z.string(),
  quantity: z.number(),
  weight_kg: z.string().nullable(),
  price: z.string().nullable(),
  comment: z.string(),
  needs_review: z.boolean(),
  position: z.number(),
  modifiers: z.array(CrmOrderItemModifierSchema),
  lines: z.array(CrmOrderItemLineSchema),
});

export const CrmPhoneSchema = z.object({
  e164: z.string(),
  tel: z.string().nullable(),
  whatsapp: z.string().nullable(),
  telegram: z.string().nullable(),
  party: z.enum(["recipient", "sender"]),
});

export const CrmOrderSchema = z.object({
  id: z.number(),
  client_token: z.string(),
  date: z.string(),
  time_start: z.string().nullable(),
  time_end: z.string().nullable(),
  when_ready: z.boolean(),
  contact: z.string(),
  phones: z.array(CrmPhoneSchema),
  nickname: z.string(),
  delivery_address: z.string(),
  delivery_distance_meters: z.number().nullable(),
  delivery_duration_seconds: z.number().nullable(),
  fulfillment_type: z.enum(["delivery", "pickup"]),
  status: z.enum(["unconfirmed", "new", "in_work", "ready", "client_approved", "in_delivery", "delivered"]),
  taken_by_name: z.string().nullable(),
  taken_by_telegram_url: z.string().nullable(),
  taken_by_gender: z.enum(["male", "female"]).nullable(),
  created_by_name: z.string().nullable(),
  created_by_telegram_url: z.string().nullable(),
  created_by_gender: z.enum(["male", "female"]).nullable(),
  delivered_by_name: z.string().nullable(),
  delivered_by_telegram_url: z.string().nullable(),
  delivered_by_gender: z.enum(["male", "female"]).nullable(),
  weight: z.string(),
  filling: z.string(),
  description: z.string(),
  internal_description: z.string(),
  cake_price: z.string(),
  prepayment: z.string(),
  is_paid: z.boolean(),
  payment_type: z.enum(["unknown", "cash", "terminal", "tbc", "bog", "tbank", "flowwow", "crypto", "paypal", "online"]),
  payment_date: z.string().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
  images: z.array(CrmOrderImageSchema),
  items: z.array(CrmOrderItemSchema),
  food_cost: z.string().optional(),
});

export const CrmOrderEventChangeSchema = z.object({
  old: z.unknown(),
  new: z.unknown(),
});

export const CrmOrderEventSchema = z.object({
  id: z.number(),
  created_at: z.string(),
  action: z.enum(["created", "updated", "deleted"]),
  source: z.enum(["crm", "admin", "website", "flowwow"]),
  actor_name: z.string().nullable(),
  actor_telegram_url: z.string().nullable(),
  actor_gender: z.enum(["male", "female"]).nullable(),
  changes: z.record(z.string(), CrmOrderEventChangeSchema),
});

export const CrmOrdersResponseSchema = z.object({
  date: z.string(),
  orders: z.array(CrmOrderSchema),
});

export const CrmMonthlyOrdersResponseSchema = z.object({
  month: z.string(),
  orders: z.array(CrmOrderSchema),
});

export const CrmUnconfirmedOrdersResponseSchema = z.object({
  orders: z.array(CrmOrderSchema),
});

export const CrmMapOrderRangeSchema = z.enum(["next_3_hours", "today"]);

export const CrmMapOrderSchema = z.object({
  id: z.number(),
  date: z.string(),
  time_start: z.string().nullable(),
  time_end: z.string().nullable(),
  when_ready: z.boolean(),
  filling: z.string(),
  weight: z.string(),
  description: z.string(),
  fulfillment_type: z.enum(["delivery", "pickup"]),
  status: z.enum(["unconfirmed", "new", "in_work", "ready", "client_approved", "in_delivery", "delivered"]),
  lat: z.number(),
  lng: z.number(),
  image: ResponsiveImageSchema.nullable(),
  delivery_distance_meters: z.number().nullable(),
  delivery_duration_seconds: z.number().nullable(),
});

export const CrmMapOrdersResponseSchema = z.object({
  range: CrmMapOrderRangeSchema,
  orders: z.array(CrmMapOrderSchema),
});

export const CrmExpensesDaySchema = z.object({
  date: z.string(),
  salary: z.string(),
  rent: z.string(),
});

export const CrmExpensesMonthSchema = z.object({
  month: z.string(),
  salary: z.string(),
  rent: z.string(),
  by_date: z.record(
    z.string(),
    z.object({
      salary: z.string(),
      rent: z.string(),
    }),
  ),
});

export const CrmSalaryEmployeeSchema = z.object({
  id: z.number(),
  name: z.string(),
  hours: z.string(),
  money: z.string(),
});

export const CrmSalaryPeriodSchema = z.object({
  start: z.string(),
  end: z.string(),
  employees: z.array(CrmSalaryEmployeeSchema),
  total_hours: z.string(),
  total_money: z.string(),
});

export const CrmSalariesSchema = z.object({
  month: z.string(),
  periods: z.array(CrmSalaryPeriodSchema),
  total_hours: z.string(),
  total_money: z.string(),
});

export const FinanceTransactionSchema = z.object({
  id: z.number(),
  date: z.string(),
  amount: z.string(),
  kind: z.enum([
    "income",
    "expense",
    "transfer",
    "withdrawal",
    "investment",
    "correction",
    "other",
  ]),
  income_type: z.string(),
  expense_type: z.string(),
  account: z.object({
    id: z.number(),
    name: z.string(),
    kind: z.string(),
    bank_name: z.string(),
    iban: z.string(),
    currency: z.string(),
  }),
  counterparty_name: z.string(),
  counterparty_iban: z.string(),
  description: z.string(),
  external_id: z.string(),
  transfer_id: z.string().nullable(),
  flowwow_order_number: z.number().nullable(),
  crm_orders: z.array(
    z.object({
      id: z.number(),
      date: z.string(),
      contact: z.string(),
      weight: z.string(),
      filling: z.string(),
      cake_price: z.string(),
    }),
  ),
  matched_account: z
    .object({
      id: z.number(),
      name: z.string(),
      currency: z.string(),
    })
    .nullable(),
  matched_transaction: z
    .object({
      id: z.number(),
      date: z.string(),
      amount: z.string(),
      account: z.object({
        id: z.number(),
        name: z.string(),
        currency: z.string(),
      }),
      counterparty_name: z.string(),
      description: z.string(),
    })
    .nullable(),
  created_at: z.string(),
  updated_at: z.string(),
});

export const FinanceTransactionsResponseSchema = z.object({
  date: z.string().nullable(),
  month: z.string().nullable(),
  transactions: z.array(FinanceTransactionSchema),
});

export const FinanceAccountSchema = z.object({
  id: z.number(),
  name: z.string(),
  kind: z.string(),
  bank_name: z.string(),
  iban: z.string(),
  currency: z.string(),
});

export const FinanceTransactionSearchResultSchema = z.object({
  id: z.number(),
  date: z.string(),
  amount: z.string(),
  account: z.object({
    id: z.number(),
    name: z.string(),
    currency: z.string(),
  }),
  counterparty_name: z.string(),
  description: z.string(),
});

export const ExchangeRatesSchema = z.object({
  date: z.string(),
  rates: z.record(z.string(), z.string()),
});

export const ResolveYandexAddressResponseSchema = z.object({
  url: z.string(),
});

export const ResolveGoogleAddressResponseSchema = z.object({
  url: z.string(),
});

export const CrmClientOrderSchema = z.object({
  id: z.number(),
  date: z.string(),
  time_start: z.string().nullable(),
  time_end: z.string().nullable(),
  when_ready: z.boolean(),
  contact: z.string(),
  phones: z.array(CrmPhoneSchema),
  nickname: z.string(),
  delivery_address: z.string(),
  delivery_duration_seconds: z.number().nullable(),
  fulfillment_type: z.enum(["delivery", "pickup"]),
  status: z.enum(["unconfirmed", "new", "in_work", "ready", "client_approved", "in_delivery", "delivered"]),
  weight: z.string(),
  filling: z.string(),
  description: z.string(),
  cake_price: z.string(),
  prepayment: z.string(),
  is_paid: z.boolean(),
  payment_type: z.enum(["unknown", "cash", "terminal", "tbc", "bog", "tbank", "flowwow", "crypto", "paypal", "online"]),
  images: z.array(CrmOrderImageSchema),
  google_maps_url: z.string().nullable(),
});

export type Category = z.infer<typeof CategorySchema>;
export type CategoryLanding = z.infer<typeof CategoryLandingSchema>;
export type CategoryDetail = z.infer<typeof CategoryDetailSchema>;
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
export type SessionUser = z.infer<typeof SessionUserSchema>;
export type AttendanceEvent = z.infer<typeof AttendanceEventSchema>;
export type AttendanceSummary = z.infer<typeof AttendanceSummarySchema>;
export type CrmOrderImage = z.infer<typeof CrmOrderImageSchema>;
export type CrmOrder = z.infer<typeof CrmOrderSchema>;
export type CrmOrderEvent = z.infer<typeof CrmOrderEventSchema>;
export type CrmClientOrder = z.infer<typeof CrmClientOrderSchema>;
export type CrmOrdersResponse = z.infer<typeof CrmOrdersResponseSchema>;
export type CrmMonthlyOrdersResponse = z.infer<typeof CrmMonthlyOrdersResponseSchema>;
export type CrmUnconfirmedOrdersResponse = z.infer<typeof CrmUnconfirmedOrdersResponseSchema>;
export type CrmMapOrderRange = z.infer<typeof CrmMapOrderRangeSchema>;
export type CrmMapOrder = z.infer<typeof CrmMapOrderSchema>;
export type CrmMapOrdersResponse = z.infer<typeof CrmMapOrdersResponseSchema>;
export type CrmExpensesDay = z.infer<typeof CrmExpensesDaySchema>;
export type CrmExpensesMonth = z.infer<typeof CrmExpensesMonthSchema>;
export type CrmSalaryEmployee = z.infer<typeof CrmSalaryEmployeeSchema>;
export type CrmSalaryPeriod = z.infer<typeof CrmSalaryPeriodSchema>;
export type CrmSalaries = z.infer<typeof CrmSalariesSchema>;
export type FinanceTransaction = z.infer<typeof FinanceTransactionSchema>;
export type FinanceTransactionsResponse = z.infer<typeof FinanceTransactionsResponseSchema>;
export type FinanceAccount = z.infer<typeof FinanceAccountSchema>;
export type FinanceTransactionSearchResult = z.infer<typeof FinanceTransactionSearchResultSchema>;

export type FinanceTransactionWriteBody = {
  date: string;
  account_id: number;
  amount: string;
  kind: FinanceTransaction["kind"];
  income_type: string;
  expense_type: string;
  counterparty_name: string;
  counterparty_iban: string;
  description: string;
  transfer_pair: "none" | "link" | "create";
  matched_transaction_id: number | null;
  counterpart: {
    account_id: number;
    date: string;
    amount: string;
  } | null;
};
export type ExchangeRates = z.infer<typeof ExchangeRatesSchema>;
export type ResolveYandexAddressResponse = z.infer<typeof ResolveYandexAddressResponseSchema>;
export type ResolveGoogleAddressResponse = z.infer<typeof ResolveGoogleAddressResponseSchema>;

export type UpdateCrmOrderBody = {
  status?: CrmOrder["status"];
  is_paid?: boolean;
  take_in_work?: boolean;
  payment_type?: CrmOrder["payment_type"];
};

export type CrmOrderPaymentType = CrmOrder["payment_type"];
export type CrmOrderStatus = CrmOrder["status"];

export type CrmOrderWriteFields = {
  date: string;
  time_start: string | null;
  time_end: string | null;
  when_ready: boolean;
  contact: string;
  nickname: string;
  delivery_address: string;
  fulfillment_type: "delivery" | "pickup";
  status: CrmOrderStatus;
  weight: string;
  filling: string;
  description: string;
  internal_description: string;
  cake_price: string;
  prepayment: string;
  is_paid: boolean;
  payment_type: CrmOrderPaymentType;
  payment_date: string | null;
};

export type LoginBody = {
  username: string;
  password: string;
};

export type AttendanceEventType = "arrival" | "departure";

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

export type CheckoutSchedule = {
  mode: "slot";
  date: string;
  start_time: string;
  end_time: string;
};

export type PlaceOrderBody = {
  fulfillment_type: FulfillmentType;
  address?: OrderAddress;
  pickup_location_id?: number;
  schedule_mode: "slot";
  schedule_date?: string;
  schedule_start_time?: string;
  schedule_end_time?: string;
  payment_method: PaymentMethod;
  customer_name: string;
  customer_phone: string;
  customer_email: string;
  customer_instagram?: string;
  customer_telegram?: string;
  comment: string;
  promo_code?: string;
  locale: string;
};

export type StartPaymentBody = {
  number: string;
  token: string;
};

export type StartPaymentResponse = {
  action_url: string;
  fields: Record<string, string>;
};

export type PreviewOrderBody = {
  fulfillment_type: FulfillmentType;
  promo_code?: string;
};

export type CrmOrderItem = z.infer<typeof CrmOrderItemSchema>;
export type MenuUnit = z.infer<typeof MenuUnitSchema>;

export const IngredientCategorySchema = z.object({
  id: z.number(),
  name: z.string(),
  position: z.number(),
});

export const IngredientSchema = z.object({
  id: z.number(),
  name: z.string(),
  category: z.number().nullable(),
  category_name: z.string().nullable(),
  unit: MenuUnitSchema,
  avg_cost: z.string().optional(),
  is_active: z.boolean(),
});

export const RecipeLineSchema = z.object({
  id: z.number(),
  ingredient: z.number().nullable(),
  semi_product: z.number().nullable(),
  name: z.string(),
  unit: MenuUnitSchema,
  quantity: z.string(),
  loss_percent: z.string(),
});

export const MenuImageSchema = z.object({
  id: z.number(),
  image: ResponsiveImageSchema,
  position: z.number(),
});

export const SemiProductSchema = z.object({
  id: z.number(),
  name: z.string(),
  unit: MenuUnitSchema,
  yield_quantity: z.string(),
  is_produced: z.boolean(),
  avg_cost: z.string().optional(),
  is_active: z.boolean(),
  method: z.string(),
  images: z.array(MenuImageSchema),
  lines: z.array(RecipeLineSchema),
});

export const ModifierSchema = z.object({
  id: z.number(),
  name: z.string(),
  catalog_option: z.number().nullable(),
  catalog_option_label: z.string().nullable(),
  ingredient: z.number().nullable(),
  semi_product: z.number().nullable(),
  is_active: z.boolean(),
});

export const ModifierGroupSchema = z.object({
  id: z.number(),
  name: z.string(),
  selection_type: z.enum(["single", "multi"]),
  is_required: z.boolean(),
  min_selections: z.number(),
  max_selections: z.number().nullable(),
  position: z.number(),
  modifiers: z.array(ModifierSchema),
});

export const TechCardGroupSchema = z.object({
  id: z.number(),
  group: z.number(),
  group_name: z.string(),
  selection_type: z.enum(["single", "multi"]),
  is_required: z.boolean().nullable(),
  effective_is_required: z.boolean(),
  min_selections: z.number(),
  max_selections: z.number().nullable(),
  modifiers: z.array(z.object({ id: z.number(), name: z.string() })),
});

export const TechCardModifierLineSchema = RecipeLineSchema.extend({
  modifier: z.number(),
  scales_by_weight: z.boolean(),
});

export const TechCardCategorySchema = z.object({
  id: z.number(),
  name: z.string(),
  position: z.number(),
});

export const TechCardSchema = z.object({
  id: z.number(),
  name: z.string(),
  category: z.number().nullable(),
  category_name: z.string().nullable(),
  kind: z.enum(["weighted", "piece"]),
  basis_weight_kg: z.string().nullable(),
  basis_quantity: z.number().int().nullable(),
  method: z.string(),
  is_active: z.boolean(),
  lines: z.array(RecipeLineSchema),
  modifier_groups: z.array(TechCardGroupSchema),
  modifier_lines: z.array(TechCardModifierLineSchema),
  missing_modifiers: z.array(z.number()),
  products: z.array(z.object({ id: z.number(), name: z.string() })),
  images: z.array(MenuImageSchema),
  base_cost: z.string().optional(),
});

export const TechCardCostSchema = z.object({ cost: z.string() });

export const MissingModifierLineSchema = z.object({
  tech_card: z.number(),
  tech_card_name: z.string(),
  modifier: z.number(),
  modifier_name: z.string(),
  group_name: z.string(),
});

export const CatalogOptionSchema = z.object({
  id: z.number(),
  label: z.string(),
  weight_kg: z.string().nullable(),
  modifier: z.number().nullable(),
});

export type IngredientCategory = z.infer<typeof IngredientCategorySchema>;
export type Ingredient = z.infer<typeof IngredientSchema>;
export type RecipeLine = z.infer<typeof RecipeLineSchema>;
export type MenuImage = z.infer<typeof MenuImageSchema>;
export type SemiProduct = z.infer<typeof SemiProductSchema>;
export type Modifier = z.infer<typeof ModifierSchema>;
export type ModifierGroup = z.infer<typeof ModifierGroupSchema>;
export type TechCardGroup = z.infer<typeof TechCardGroupSchema>;
export type TechCardModifierLine = z.infer<typeof TechCardModifierLineSchema>;
export type TechCardCategory = z.infer<typeof TechCardCategorySchema>;
export type TechCard = z.infer<typeof TechCardSchema>;
export type MissingModifierLine = z.infer<typeof MissingModifierLineSchema>;
export type CatalogOption = z.infer<typeof CatalogOptionSchema>;

export type ComponentRefBody = {
  ingredient: number | null;
  semi_product: number | null;
};

export type RecipeLineBody = ComponentRefBody & {
  quantity: string;
  loss_percent: string;
};

export type IngredientCategoryBody = { name: string; position: number };

export type IngredientBody = {
  name: string;
  category: number | null;
  unit: MenuUnit;
  is_active: boolean;
};

export type SemiProductBody = {
  name: string;
  unit: MenuUnit;
  yield_quantity: string;
  is_produced: boolean;
  is_active: boolean;
  method: string;
  lines: RecipeLineBody[];
};

export type ModifierGroupBody = {
  name: string;
  selection_type: "single" | "multi";
  is_required: boolean;
  min_selections: number;
  max_selections: number | null;
  position: number;
  modifiers: {
    id: number | null;
    name: string;
    catalog_option: number | null;
    ingredient: number | null;
    semi_product: number | null;
    is_active: boolean;
  }[];
};

export type TechCardCategoryBody = { name: string; position: number };

export type TechCardBody = {
  name: string;
  category: number | null;
  kind: "weighted" | "piece";
  basis_weight_kg: string | null;
  basis_quantity: number | null;
  method: string;
  is_active: boolean;
  lines: RecipeLineBody[];
  modifier_groups: { group: number; is_required: boolean | null }[];
  modifier_lines: (RecipeLineBody & { modifier: number; scales_by_weight: boolean })[];
};

export type CrmOrderItemBody = {
  tech_card: number | null;
  name: string;
  quantity: number;
  weight_kg: string | null;
  price: string | null;
  comment: string;
  needs_review: boolean;
  modifiers: { modifier: number; quantity: number }[];
  lines: (ComponentRefBody & { quantity: string })[];
};

export const InventoryComponentLineSchema = z.object({
  id: z.number(),
  ingredient: z.number().nullable(),
  semi_product: z.number().nullable(),
  name: z.string(),
  unit: MenuUnitSchema,
  quantity: z.string(),
});

export const SupplierSchema = z.object({
  id: z.number(),
  name: z.string(),
  phone: z.string(),
  comment: z.string(),
});

export const WriteOffReasonSchema = z.object({
  id: z.number(),
  name: z.string(),
});

export const SupplyTransactionSchema = z.object({
  id: z.number(),
  date: z.string(),
  amount: z.string(),
  counterparty_name: z.string(),
  description: z.string(),
  account_name: z.string(),
});

export const SupplySchema = z.object({
  id: z.number(),
  date: z.string(),
  supplier: z.number().nullable(),
  supplier_name: z.string().nullable(),
  financial_transaction: SupplyTransactionSchema.nullable(),
  comment: z.string(),
  created_at: z.string(),
  total: z.string(),
  lines: z.array(
    z.object({
      id: z.number(),
      ingredient: z.number(),
      name: z.string(),
      unit: MenuUnitSchema,
      quantity: z.string(),
      total: z.string(),
    }),
  ),
});

export const StockMovementKindSchema = z.enum([
  "supply",
  "production_in",
  "production_out",
  "order",
  "write_off",
  "inventory",
]);

export const StockMovementSchema = z.object({
  id: z.number(),
  date: z.string(),
  kind: StockMovementKindSchema,
  ingredient: z.number().nullable(),
  semi_product: z.number().nullable(),
  name: z.string(),
  unit: MenuUnitSchema,
  quantity: z.string(),
  document: z.object({
    type: z.enum(["supply", "production", "crm_order", "write_off", "inventory_count"]),
    id: z.number(),
  }),
  unit_cost: z.string().optional(),
});

export const ProductionSchema = z.object({
  id: z.number(),
  date: z.string(),
  semi_product: z.number(),
  semi_product_name: z.string(),
  unit: MenuUnitSchema,
  quantity: z.string(),
  comment: z.string(),
  created_at: z.string(),
  created_by_name: z.string().nullable(),
  consumed: z.array(StockMovementSchema),
  unit_cost: z.string().nullable().optional(),
});

export const WriteOffSchema = z.object({
  id: z.number(),
  date: z.string(),
  reason: z.number(),
  reason_name: z.string(),
  comment: z.string(),
  created_at: z.string(),
  created_by_name: z.string().nullable(),
  lines: z.array(InventoryComponentLineSchema),
  total_cost: z.string().optional(),
});

export const InventoryCountSchema = z.object({
  id: z.number(),
  date: z.string(),
  status: z.enum(["draft", "closed"]),
  comment: z.string(),
  created_at: z.string(),
  closed_at: z.string().nullable(),
  created_by_name: z.string().nullable(),
  lines: z.array(
    z.object({
      id: z.number(),
      ingredient: z.number().nullable(),
      semi_product: z.number().nullable(),
      name: z.string(),
      unit: MenuUnitSchema,
      actual_quantity: z.string(),
      expected_quantity: z.string().nullable(),
      unit_cost: z.string().nullable().optional(),
    }),
  ),
});

export const StockRowSchema = z.object({
  ingredient: z.number().nullable(),
  semi_product: z.number().nullable(),
  name: z.string(),
  unit: MenuUnitSchema,
  category_name: z.string().nullable(),
  is_active: z.boolean(),
  quantity: z.string(),
  avg_cost: z.string().optional(),
  value: z.string().optional(),
});

export type Supplier = z.infer<typeof SupplierSchema>;
export type WriteOffReason = z.infer<typeof WriteOffReasonSchema>;
export type SupplyTransaction = z.infer<typeof SupplyTransactionSchema>;
export type Supply = z.infer<typeof SupplySchema>;
export type StockMovementKind = z.infer<typeof StockMovementKindSchema>;
export type StockMovement = z.infer<typeof StockMovementSchema>;
export type Production = z.infer<typeof ProductionSchema>;
export type WriteOff = z.infer<typeof WriteOffSchema>;
export type InventoryCount = z.infer<typeof InventoryCountSchema>;
export type StockRow = z.infer<typeof StockRowSchema>;

export type SupplierBody = { name: string; phone: string; comment: string };
export type WriteOffReasonBody = { name: string };

export type SupplyBody = {
  date: string;
  supplier: number | null;
  financial_transaction: number | null;
  comment: string;
  lines: { ingredient: number; quantity: string; total: string }[];
};

export type ProductionBody = {
  date: string;
  semi_product: number;
  quantity: string;
  comment: string;
};

export type WriteOffBody = {
  date: string;
  reason: number;
  comment: string;
  lines: (ComponentRefBody & { quantity: string })[];
};

export type InventoryCountBody = {
  date: string;
  comment: string;
  lines: (ComponentRefBody & { actual_quantity: string; unit_cost: string | null })[];
};
