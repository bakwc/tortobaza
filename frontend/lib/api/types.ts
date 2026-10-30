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

export const PayPalConfigSchema = z.object({
  enabled: z.boolean(),
  client_id: z.string(),
});

export const PayPalCreateResponseSchema = z.object({
  paypal_order_id: z.string(),
  amount_usd: z.string(),
  exchange_rate: z.string(),
});

export const PayPalCaptureResponseSchema = z.object({
  status: z.string(),
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

export const EmployeeSchema = z.object({
  id: z.number(),
  username: z.string(),
  first_name: z.string(),
  last_name: z.string(),
  email: z.string(),
  is_active: z.boolean(),
  is_staff: z.boolean(),
  hourly_rate: z.string(),
  monthly_rate: z.string(),
  can_login: z.boolean(),
  telegram_username: z.string(),
  internal_name: z.string(),
  gender: z.enum(["male", "female"]),
  is_finance_admin: z.boolean(),
  is_active_courier: z.boolean(),
  pushover_user: z.string(),
  position: z.string(),
  in_schedule: z.boolean(),
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

export const ScheduleDayTypeSchema = z.enum(["work", "off", "vacation", "sick"]);

export const ScheduleEmployeeSchema = z.object({
  id: z.number(),
  name: z.string(),
  position: z.string(),
  days: z.record(z.string(), ScheduleDayTypeSchema),
});

export const ScheduleGridSchema = z.object({
  start: z.string(),
  end: z.string(),
  employees: z.array(ScheduleEmployeeSchema),
});

export const TimesheetCellSchema = z.object({
  day_type: ScheduleDayTypeSchema.nullable(),
  hours: z.string(),
  mismatch: z.boolean(),
});

export const TimesheetEmployeeSchema = z.object({
  id: z.number(),
  name: z.string(),
  position: z.string(),
  total_hours: z.string(),
  days: z.record(z.string(), TimesheetCellSchema),
});

export const TimesheetGridSchema = z.object({
  start: z.string(),
  end: z.string(),
  employees: z.array(TimesheetEmployeeSchema),
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
  is_gift: z.boolean(),
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
  delivery_price: z.string(),
  prepayment: z.string(),
  is_paid: z.boolean(),
  payment_type: z.enum(["unknown", "cash", "terminal", "tbc", "bog", "tbank", "flowwow", "crypto", "paypal", "online"]),
  payment_date: z.string().nullable(),
  payment_url: z.string().nullable(),
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

export const AuditEventSchema = z.object({
  id: z.number(),
  created_at: z.string(),
  actor_id: z.number().nullable(),
  actor_name: z.string().nullable(),
  action: z.enum(["created", "updated", "deleted"]),
  app_label: z.string(),
  model: z.string(),
  object_id: z.string(),
  object_label: z.string(),
  database: z.string(),
  source: z.enum(["user", "crm", "admin", "website", "flowwow"]),
  changes: z.record(z.string(), CrmOrderEventChangeSchema),
});

export const AuditEventsResponseSchema = z.object({
  page: z.number(),
  pages: z.number(),
  results: z.array(AuditEventSchema),
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

export const CrmSalaryEmployeeSchema = z.object({
  id: z.number(),
  name: z.string(),
  hours: z.string(),
  money: z.string(),
});

export const CrmSalaryPeriodEmployeeSchema = CrmSalaryEmployeeSchema.extend({
  position: z.string(),
});

export const CrmExpensesBreakdownSchema = z.object({
  salary: z.string(),
  rent: z.string(),
  employees: z.array(CrmSalaryEmployeeSchema),
});

export const CrmExpensesDaySchema = z.object({
  date: z.string(),
  salary: z.string(),
  rent: z.string(),
  employees: z.array(CrmSalaryEmployeeSchema),
});

export const CrmExpensesMonthSchema = z.object({
  month: z.string(),
  salary: z.string(),
  rent: z.string(),
  employees: z.array(CrmSalaryEmployeeSchema),
  by_date: z.record(z.string(), CrmExpensesBreakdownSchema),
});

export const CrmSalaryPeriodSchema = z.object({
  start: z.string(),
  end: z.string(),
  employees: z.array(CrmSalaryPeriodEmployeeSchema),
  hourly_hours: z.string(),
  hourly_money: z.string(),
  monthly_hours: z.string(),
  monthly_money: z.string(),
});

export const CrmSalariesSchema = z.object({
  month: z.string(),
  periods: z.array(CrmSalaryPeriodSchema),
  hourly_hours: z.string(),
  hourly_money: z.string(),
  monthly_hours: z.string(),
  monthly_money: z.string(),
});

export const AnalyticsTotalsSchema = z.object({
  orders: z.number(),
  revenue: z.string(),
  average_check: z.string().nullable(),
  kilograms: z.string(),
  weight_unknown: z.number(),
});

export const AnalyticsOverviewTotalsSchema = AnalyticsTotalsSchema.extend({
  months: z.number(),
});

export const AnalyticsOverviewMonthSchema = z.object({
  month: z.string(),
  orders: z.number(),
  revenue: z.string(),
  average_check: z.string().nullable(),
  kilograms: z.string(),
  weight_unknown: z.number(),
  price_per_kg: z.string().nullable(),
  partial: z.boolean(),
});

export const AnalyticsChannelSliceSchema = z.object({
  orders: z.number(),
  revenue: z.string(),
});

export const AnalyticsOverviewChannelSchema = z.object({
  month: z.string(),
  flowwow: AnalyticsChannelSliceSchema,
  website: AnalyticsChannelSliceSchema,
  direct: AnalyticsChannelSliceSchema,
});

export const AnalyticsOverviewPaymentSchema = z.object({
  type: z.enum(["unknown", "cash", "terminal", "tbc", "bog", "tbank", "flowwow", "crypto", "paypal", "online"]),
  orders: z.number(),
  revenue: z.string(),
});

export const AnalyticsOverviewSchema = z.object({
  first_date: z.string().nullable(),
  today: z.string(),
  current_month: z.string(),
  totals: AnalyticsOverviewTotalsSchema,
  months: z.array(AnalyticsOverviewMonthSchema),
  channels: z.array(AnalyticsOverviewChannelSchema),
  payments: z.array(AnalyticsOverviewPaymentSchema),
});

export const AnalyticsBaselineSchema = z.object({
  days: z.number(),
  orders_median: z.string().nullable(),
  orders_p90: z.string().nullable(),
  orders_max: z.string().nullable(),
  kilograms_median: z.string().nullable(),
  kilograms_p90: z.string().nullable(),
  kilograms_max: z.string().nullable(),
});

export const AnalyticsDaySchema = z.object({
  date: z.string(),
  orders: z.number(),
  kilograms: z.string(),
  weight_unknown: z.number(),
});

export const AnalyticsSlotsSchema = z.object({
  interval: z.number(),
  exact: z.number(),
  missing: z.number(),
  morning: z.number(),
  day: z.number(),
  evening: z.number(),
  hours: z.array(z.object({ hour: z.number(), orders: z.number() })),
});

export const AnalyticsHorizonDaySchema = z.object({
  date: z.string(),
  orders: z.number(),
  kilograms: z.string(),
});

export const AnalyticsLoadSchema = z.object({
  month: z.string(),
  start: z.string(),
  end: z.string(),
  baseline: AnalyticsBaselineSchema,
  days: z.array(AnalyticsDaySchema),
  slots: AnalyticsSlotsSchema,
  lead: z.object({
    median: z.string().nullable(),
    same_day: z.number(),
    next_day: z.number(),
    long: z.number(),
  }),
  horizon: z.object({
    today: z.string(),
    tomorrow: AnalyticsHorizonDaySchema,
    day_after: AnalyticsHorizonDaySchema,
  }),
});

export const AnalyticsMonthRowSchema = z.object({
  month: z.string(),
  new_orders: z.number(),
  new_revenue: z.string(),
  return_orders: z.number(),
  return_revenue: z.string(),
});

export const AnalyticsCohortCellSchema = z.object({
  offset: z.number(),
  count: z.number().nullable(),
  share: z.string().nullable(),
  observed: z.boolean(),
});

export const AnalyticsCustomerSchema = z.object({
  name: z.string(),
  phones: z.array(z.string()),
  orders: z.number(),
  revenue: z.string(),
  first: z.string(),
  last: z.string(),
  order_id: z.number(),
});

export const AnalyticsFrequencyBucketSchema = z.object({
  clients: z.number(),
  revenue: z.string(),
});

export const AnalyticsProductMetricsSchema = z.object({
  quantity: z.number(),
  orders: z.number(),
  kilograms: z.string(),
});

export const AnalyticsProductKindSchema = z.enum(["cake", "bento", "cupcake", "macaron", "addon", "other"]);

export const AnalyticsProductsSchema = z.object({
  month: z.string(),
  start: z.string(),
  end: z.string(),
  coverage: z.object({
    orders: z.number(),
    parsed: z.number(),
  }),
  kinds: z.array(
    AnalyticsProductMetricsSchema.extend({
      kind: AnalyticsProductKindSchema,
    }),
  ),
  positions: z.array(
    AnalyticsProductMetricsSchema.extend({
      kind: AnalyticsProductKindSchema,
      name: z.string(),
    }),
  ),
  fillings: z.array(
    AnalyticsProductMetricsSchema.extend({
      filling: z.string(),
    }),
  ),
  weights: z.array(
    AnalyticsProductMetricsSchema.extend({
      kg: z.string(),
    }),
  ),
  weight_unknown: z.number(),
});

export const AnalyticsStaffPeriodSchema = z.object({
  hourly_money: z.string(),
  monthly_money: z.string(),
  money: z.string(),
  revenue: z.string(),
  kilograms: z.string(),
  hours: z.string(),
  shifts: z.number(),
  salary_share: z.string().nullable(),
  money_per_kg: z.string().nullable(),
  kg_per_hour: z.string().nullable(),
});

export const AnalyticsStaffBakerSchema = z.object({
  id: z.number(),
  name: z.string(),
  kilograms: z.string(),
  orders: z.number(),
});

export const AnalyticsEmployeeSchema = z.object({
  id: z.number(),
  name: z.string(),
  monthly: z.boolean(),
  shifts: z.number(),
  hours: z.string(),
  average_shift: z.string().nullable(),
  money: z.string(),
  money_share: z.string().nullable(),
  made: z.number(),
  made_kilograms: z.string(),
  arrival: z.string().nullable(),
  departure: z.string().nullable(),
  kinds: z.array(
    z.object({
      kind: AnalyticsProductKindSchema,
      quantity: z.number(),
    }),
  ),
  production_minutes: z.string().nullable(),
  production_orders: z.number(),
});

export const AnalyticsEmployeesSchema = z.object({
  month: z.string(),
  totals: AnalyticsStaffPeriodSchema,
  previous: AnalyticsStaffPeriodSchema,
  gaps: z.object({
    without_baker: z.number(),
    unclosed_shifts: z.number(),
    without_composition: z.number(),
    without_production: z.number(),
  }),
  months: z.array(
    AnalyticsStaffPeriodSchema.pick({
      hourly_money: true,
      monthly_money: true,
      revenue: true,
      kilograms: true,
      hours: true,
      salary_share: true,
      money_per_kg: true,
      kg_per_hour: true,
    }).extend({
      month: z.string(),
      partial: z.boolean(),
      bakers: z.array(AnalyticsStaffBakerSchema),
      unassigned_kilograms: z.string(),
    }),
  ),
  days: z.array(
    z.object({
      date: z.string(),
      hours: z.string(),
      kilograms: z.string(),
      kg_per_hour: z.string().nullable(),
      bakers: z.array(
        z.object({
          id: z.number(),
          name: z.string(),
          kilograms: z.string(),
        }),
      ),
      unassigned_kilograms: z.string(),
    }),
  ),
  weekdays: z.array(
    z.object({
      weekday: z.number(),
      hours: z.string(),
      kilograms: z.string(),
    }),
  ),
  employees: z.array(AnalyticsEmployeeSchema),
  timesheet: z.array(
    z.object({
      id: z.number(),
      name: z.string(),
      days: z.array(
        z.object({
          date: z.string(),
          hours: z.string(),
          open: z.boolean(),
        }),
      ),
    }),
  ),
});

export const AnalyticsClientsSchema = z.object({
  orders: z.number(),
  known_orders: z.number(),
  unknown_orders: z.number(),
  clients: z.number(),
  repeat_clients: z.number(),
  known_revenue: z.string(),
  repeat_revenue: z.string(),
  months: z.array(AnalyticsMonthRowSchema),
  cohorts: z.array(
    z.object({
      month: z.string(),
      clients: z.number(),
      cells: z.array(AnalyticsCohortCellSchema),
    }),
  ),
  gaps: z.object({
    median: z.string().nullable(),
    bins: z.array(z.object({ label: z.string(), count: z.number() })),
  }),
  frequency: z.object({
    once: AnalyticsFrequencyBucketSchema,
    twice: AnalyticsFrequencyBucketSchema,
    more: AnalyticsFrequencyBucketSchema,
  }),
  top_revenue: z.array(AnalyticsCustomerSchema),
  top_orders: z.array(AnalyticsCustomerSchema),
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
      delivery_price: z.string(),
    }),
  ),
  waybills: z.array(
    z.object({
      id: z.number(),
      waybill_number: z.string(),
      seller_name: z.string(),
      seller_name_ru: z.string(),
      full_amount: z.string(),
      create_date: z.string(),
    }),
  ),
  invoices: z.array(
    z.object({
      id: z.number(),
      series: z.string(),
      number: z.string(),
      amount: z.string(),
      reg_dt: z.string(),
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
  is_gift: z.boolean(),
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
  delivery_price: z.string(),
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
export type Employee = z.infer<typeof EmployeeSchema>;
export type EmployeeBody = {
  username: string;
  password: string;
  first_name: string;
  last_name: string;
  email: string;
  is_active: boolean;
  is_staff: boolean;
  hourly_rate: string;
  monthly_rate: string;
  can_login: boolean;
  telegram_username: string;
  internal_name: string;
  gender: "male" | "female";
  is_finance_admin: boolean;
  is_active_courier: boolean;
  pushover_user: string;
  position: string;
  in_schedule: boolean;
};
export type AttendanceEvent = z.infer<typeof AttendanceEventSchema>;
export type AttendanceSummary = z.infer<typeof AttendanceSummarySchema>;
export type ScheduleDayType = z.infer<typeof ScheduleDayTypeSchema>;
export type ScheduleGrid = z.infer<typeof ScheduleGridSchema>;
export type TimesheetGrid = z.infer<typeof TimesheetGridSchema>;
export type ScheduleCellBody = {
  user: number;
  date: string;
  day_type: ScheduleDayType | null;
};
export type ScheduleFillBody = {
  user: number;
  start: string;
  end: string;
  cycle_start: string;
  pattern: ScheduleDayType[];
};
export type CrmOrderImage = z.infer<typeof CrmOrderImageSchema>;
export type CrmOrder = z.infer<typeof CrmOrderSchema>;
export type CrmOrderEvent = z.infer<typeof CrmOrderEventSchema>;
export type AuditEvent = z.infer<typeof AuditEventSchema>;
export type AuditEventsResponse = z.infer<typeof AuditEventsResponseSchema>;
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
export type AnalyticsOverview = z.infer<typeof AnalyticsOverviewSchema>;
export type AnalyticsOverviewPayment = z.infer<typeof AnalyticsOverviewPaymentSchema>;
export type AnalyticsLoad = z.infer<typeof AnalyticsLoadSchema>;
export type AnalyticsClients = z.infer<typeof AnalyticsClientsSchema>;
export type AnalyticsProducts = z.infer<typeof AnalyticsProductsSchema>;
export type AnalyticsEmployees = z.infer<typeof AnalyticsEmployeesSchema>;
export type AnalyticsProductKind = z.infer<typeof AnalyticsProductKindSchema>;
export type AnalyticsCustomer = z.infer<typeof AnalyticsCustomerSchema>;
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
  is_gift: boolean;
  nickname: string;
  delivery_address: string;
  fulfillment_type: "delivery" | "pickup";
  status: CrmOrderStatus;
  weight: string;
  filling: string;
  description: string;
  internal_description: string;
  cake_price: string;
  delivery_price: string;
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
export type PaymentMethod = "paypal" | "card" | "cash" | "bank_transfer";

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

export type PayPalConfig = {
  enabled: boolean;
  client_id: string;
};

export type PayPalCreateBody = {
  number: string;
  token: string;
};

export type PayPalCreateResponse = {
  paypal_order_id: string;
  amount_usd: string;
  exchange_rate: string;
};

export type PayPalCaptureBody = {
  number: string;
  token: string;
  paypal_order_id: string;
};

export type PayPalCaptureResponse = {
  status: string;
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
  cost_quantity: z.string(),
  grams_per_unit: z.string().nullable(),
  sale_price: z.string().nullable(),
  is_active: z.boolean(),
});

export const RecipeLineSchema = z.object({
  id: z.number(),
  ingredient: z.number().nullable(),
  semi_product: z.number().nullable(),
  name: z.string(),
  unit: MenuUnitSchema,
  quantity: z.string(),
  quantity_unit: MenuUnitSchema,
  loss_percent: z.string(),
  cost: z.string().optional(),
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
  cost: z.string().optional(),
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

export const TechCardSectionSchema = z.object({
  id: z.number(),
  name: z.string(),
  method: z.string(),
  position: z.number(),
  lines: z.array(RecipeLineSchema),
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
  sale_price: z.string().nullable(),
  method: z.string(),
  is_active: z.boolean(),
  lines: z.array(RecipeLineSchema),
  sections: z.array(TechCardSectionSchema),
  modifier_groups: z.array(TechCardGroupSchema),
  modifier_lines: z.array(TechCardModifierLineSchema),
  missing_modifiers: z.array(z.number()),
  products: z.array(z.object({ id: z.number(), name: z.string() })),
  images: z.array(MenuImageSchema),
  base_cost: z.string().optional(),
  cost_min: z.string().optional(),
  cost_max: z.string().optional(),
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
export type TechCardSection = z.infer<typeof TechCardSectionSchema>;
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
  quantity_unit: MenuUnit;
  loss_percent: string;
};

export type IngredientCategoryBody = { name: string; position: number };

export type IngredientBody = {
  name: string;
  category: number | null;
  unit: MenuUnit;
  is_active: boolean;
  avg_cost: string | null;
  cost_quantity: string | null;
  grams_per_unit: string | null;
  sale_price: string | null;
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
  sale_price: string | null;
  method: string;
  is_active: boolean;
  lines: RecipeLineBody[];
  sections: { name: string; method: string; lines: RecipeLineBody[] }[];
  modifier_groups: { group: number; is_required: boolean | null }[];
  modifier_lines: (RecipeLineBody & { modifier: number; scales_by_weight: boolean })[];
};

export type CrmOrderItemCostBody = {
  tech_card: number;
  quantity: number;
  weight_kg: string | null;
  modifiers: { modifier: number; quantity: number }[];
  lines: (ComponentRefBody & { quantity: string })[];
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
  finished_good: z.number().nullable(),
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

export const RecognizedReceiptLineSchema = z.object({
  original_name: z.string(),
  name_ru: z.string(),
  ingredient_id: z.number().nullable(),
  quantity: z.string(),
  unit: MenuUnitSchema,
  total: z.string(),
});

export const RecognizedReceiptSchema = z.object({
  is_itemized: z.boolean(),
  merchant_name: z.string(),
  date: z.string(),
  total: z.string(),
  supplier: z.number().nullable(),
  lines: z.array(RecognizedReceiptLineSchema),
});

export const SupplyReceiptSchema = z.object({
  id: z.number(),
  image: z.string(),
  recognized: RecognizedReceiptSchema,
});

export const SupplyWaybillSchema = z.object({
  id: z.number(),
  waybill_number: z.string(),
  create_date: z.string(),
  full_amount: z.string(),
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
  waybill: SupplyWaybillSchema.nullable(),
  receipts: z.array(z.object({ id: z.number(), image: z.string() })),
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
  finished_good: z.number().nullable(),
  name: z.string(),
  unit: MenuUnitSchema,
  quantity: z.string(),
  document: z.object({
    type: z.enum(["supply", "production", "finished_production", "crm_order", "write_off", "inventory_count"]),
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
      finished_good: z.number().nullable(),
      name: z.string(),
      unit: MenuUnitSchema,
      actual_quantity: z.string(),
      expected_quantity: z.string().nullable(),
      unit_cost: z.string().nullable().optional(),
    }),
  ),
});

export const FinishedGoodSchema = z.object({
  id: z.number(),
  name: z.string(),
  unit: MenuUnitSchema,
});

export const FinishedProductionLineSchema = z.object({
  id: z.number(),
  finished_good: z.number(),
  name: z.string(),
  tech_card: z.number(),
  weight_kg: z.string().nullable(),
  modifiers: z.array(
    z.object({
      modifier: z.number(),
      name: z.string(),
      quantity: z.number(),
    }),
  ),
  quantity: z.number(),
  unit_cost: z.string().nullable().optional(),
});

export const FinishedProductionSchema = z.object({
  id: z.number(),
  date: z.string(),
  comment: z.string(),
  created_at: z.string(),
  created_by_name: z.string().nullable(),
  lines: z.array(FinishedProductionLineSchema),
  consumed: z.array(StockMovementSchema),
});

export const StockRowSchema = z.object({
  ingredient: z.number().nullable(),
  semi_product: z.number().nullable(),
  finished_good: z.number().nullable(),
  name: z.string(),
  unit: MenuUnitSchema,
  category_name: z.string().nullable(),
  is_active: z.boolean(),
  quantity: z.string(),
  avg_cost: z.string().optional(),
  value: z.string().optional(),
});

export const RsWaybillGoodSchema = z.object({
  id: z.number(),
  rs_id: z.number(),
  name: z.string(),
  name_ru: z.string(),
  unit_id: z.number(),
  unit_txt: z.string(),
  unit_txt_ru: z.string(),
  quantity: z.string(),
  price: z.string(),
  amount: z.string(),
  bar_code: z.string(),
  a_id: z.number().nullable(),
  vat_type: z.number(),
  quantity_ext: z.string().nullable(),
  status: z.number(),
  quantity_f: z.string(),
});

export const RsLinkedTransactionSchema = z.object({
  id: z.number(),
  date: z.string(),
  amount: z.string(),
  counterparty_name: z.string(),
});

export const RsLinkedWaybillSchema = z.object({
  id: z.number(),
  waybill_number: z.string(),
  seller_name: z.string(),
  seller_name_ru: z.string(),
  full_amount: z.string(),
  create_date: z.string(),
});

export const RsLinkedInvoiceSchema = z.object({
  id: z.number(),
  series: z.string(),
  number: z.string(),
  amount: z.string(),
  reg_dt: z.string(),
});

export const RsLinkedSupplySchema = z.object({
  id: z.number(),
  date: z.string(),
  total: z.string(),
});

export const RsWaybillSchema = z.object({
  id: z.number(),
  rs_id: z.number(),
  waybill_number: z.string(),
  type: z.number(),
  status: z.number(),
  create_date: z.string(),
  activate_date: z.string(),
  begin_date: z.string(),
  delivery_date: z.string().nullable(),
  close_date: z.string().nullable(),
  buyer_tin: z.string(),
  buyer_name: z.string(),
  buyer_name_ru: z.string(),
  seller_tin: z.string(),
  seller_name: z.string(),
  seller_name_ru: z.string(),
  start_address: z.string(),
  start_address_ru: z.string(),
  end_address: z.string(),
  end_address_ru: z.string(),
  driver_tin: z.string(),
  driver_name: z.string(),
  driver_name_ru: z.string(),
  car_number: z.string(),
  reception_info: z.string(),
  reception_info_ru: z.string(),
  waybill_comment: z.string(),
  waybill_comment_ru: z.string(),
  transport_coast: z.string(),
  full_amount: z.string(),
  s_user_id: z.number(),
  par_id: z.number().nullable(),
  invoice_id: z.number().nullable(),
  is_confirmed: z.number(),
  is_corrected: z.number(),
  seller_st: z.number(),
  is_med: z.number(),
  goods: z.array(RsWaybillGoodSchema),
  invoices: z.array(RsLinkedInvoiceSchema),
  financial_transactions: z.array(RsLinkedTransactionSchema),
  supply_id: z.number().nullable(),
  supply: RsLinkedSupplySchema.nullable(),
});

export const WaybillSupplySuggestionSchema = z.object({
  ingredient_id: z.number().nullable(),
  factor: z.string(),
  unit: MenuUnitSchema,
});

export const WaybillSupplyAliasSchema = z.object({
  ingredient_id: z.number().nullable(),
  factor: z.string().nullable(),
  ignored: z.boolean(),
});

export const WaybillSupplyDraftLineSchema = z.object({
  good_id: z.number(),
  name: z.string(),
  name_ru: z.string(),
  unit_txt: z.string(),
  unit_txt_ru: z.string(),
  quantity: z.string(),
  amount: z.string(),
  bar_code: z.string(),
  alias: WaybillSupplyAliasSchema.nullable(),
  suggestions: z.array(WaybillSupplySuggestionSchema),
});

export const WaybillSupplyDraftSchema = z.object({
  date: z.string(),
  supplier: z.object({ id: z.number(), name: z.string() }).nullable(),
  supplier_name: z.string(),
  lines: z.array(WaybillSupplyDraftLineSchema),
});

export const RsInvoiceLineSchema = z.object({
  id: z.number(),
  rs_id: z.number(),
  goods: z.string(),
  goods_ru: z.string(),
  unit: z.string(),
  unit_ru: z.string(),
  quantity: z.string(),
  full_amount: z.string(),
  vat_amount: z.string(),
  excise_amount: z.string().nullable(),
  excise_id: z.number(),
  waybill_id: z.number().nullable(),
  vat_type: z.number(),
});

export const RsInvoiceSchema = z.object({
  id: z.number(),
  rs_id: z.number(),
  seller_un_id: z.number(),
  seq_num_b: z.number().nullable(),
  status: z.number(),
  was_ref: z.number(),
  series: z.string(),
  number: z.string(),
  reg_dt: z.string(),
  operation_dt: z.string(),
  s_user_id: z.number(),
  b_s_user_id: z.number(),
  doc_mos_nom: z.string(),
  seller_tin: z.string(),
  org_name: z.string(),
  org_name_ru: z.string(),
  notes: z.string(),
  notes_ru: z.string(),
  amount: z.string(),
  vat: z.string(),
  k_id: z.number(),
  agree_date: z.string().nullable(),
  agree_s_user_id: z.number().nullable(),
  ref_date: z.string().nullable(),
  ref_s_user_id: z.number().nullable(),
  note: z.string(),
  note_ru: z.string(),
  lines: z.array(RsInvoiceLineSchema),
  waybills: z.array(RsLinkedWaybillSchema),
  financial_transactions: z.array(RsLinkedTransactionSchema),
});

export const RsgePendingCountSchema = z.object({
  count: z.number(),
  section: z.enum(["waybills", "invoices", ""]),
  month: z.string(),
});

export type RsWaybillGood = z.infer<typeof RsWaybillGoodSchema>;
export type RsWaybill = z.infer<typeof RsWaybillSchema>;
export type WaybillSupplyDraftLine = z.infer<typeof WaybillSupplyDraftLineSchema>;
export type WaybillSupplyDraft = z.infer<typeof WaybillSupplyDraftSchema>;
export type WaybillSupplyBody = {
  lines: {
    good_id: number;
    ingredient: number | null;
    quantity: string | null;
    skipped: boolean;
  }[];
};
export type RsInvoiceLine = z.infer<typeof RsInvoiceLineSchema>;
export type RsInvoice = z.infer<typeof RsInvoiceSchema>;
export type RsgePendingCount = z.infer<typeof RsgePendingCountSchema>;
export type Supplier = z.infer<typeof SupplierSchema>;
export type WriteOffReason = z.infer<typeof WriteOffReasonSchema>;
export type SupplyTransaction = z.infer<typeof SupplyTransactionSchema>;
export type SupplyReceipt = z.infer<typeof SupplyReceiptSchema>;
export type Supply = z.infer<typeof SupplySchema>;
export type StockMovementKind = z.infer<typeof StockMovementKindSchema>;
export type StockMovement = z.infer<typeof StockMovementSchema>;
export type Production = z.infer<typeof ProductionSchema>;
export type FinishedGood = z.infer<typeof FinishedGoodSchema>;
export type FinishedProduction = z.infer<typeof FinishedProductionSchema>;
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
  receipts: number[];
};

export type ProductionBody = {
  date: string;
  semi_product: number;
  quantity: string;
  comment: string;
};

export type StockComponentBody = ComponentRefBody & { finished_good: number | null };

export type FinishedProductionBody = {
  date: string;
  comment: string;
  lines: {
    tech_card: number;
    weight_kg: string | null;
    modifiers: { modifier: number; quantity: number }[];
    quantity: number;
  }[];
};

export type WriteOffBody = {
  date: string;
  reason: number;
  comment: string;
  lines: (StockComponentBody & { quantity: string })[];
};

export type InventoryCountBody = {
  date: string;
  comment: string;
  lines: (StockComponentBody & { actual_quantity: string; unit_cost: string | null })[];
};
