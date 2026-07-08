import {
  AttendanceEventSchema,
  AttendanceSummarySchema,
  CartSchema,
  CategorySchema,
  FulfillmentOptionsSchema,
  OrderPreviewSchema,
  OrderSchema,
  PickupLocationSchema,
  ProductDetailSchema,
  ProductsPageSchema,
  PromoValidationSchema,
  SessionUserSchema,
  StartPaymentResponseSchema,
  LibertyPaymentEnabledSchema,
  type AddCartItemBody,
  type AttendanceEvent,
  type AttendanceEventType,
  type AttendanceSummary,
  type Cart,
  type Category,
  type FulfillmentOptions,
  type FulfillmentType,
  type LoginBody,
  type Order,
  type OrderPreview,
  type PickupLocation,
  type PlaceOrderBody,
  type PreviewOrderBody,
  type ProductDetail,
  type ProductsPage,
  type PromoValidation,
  type SessionUser,
  type StartPaymentBody,
  type StartPaymentResponse,
  type UpdateCartItemBody,
} from "./types";
import { z } from "zod";

export type Fetcher = <T>(
  path: string,
  options?: {
    method?: string;
    body?: string;
    searchParams?: Record<string, string | number | undefined | null>;
    headers?: HeadersInit;
    cache?: RequestCache;
    next?: { revalidate?: number; tags?: string[] };
  },
) => Promise<T>;

function parse<T>(schema: z.ZodType<T>, raw: unknown): T {
  return schema.parse(raw);
}

export function endpoints(fetcher: Fetcher) {
  return {
    async getCategories(): Promise<Category[]> {
      const raw = await fetcher<unknown>("/api/categories/");
      return parse(z.array(CategorySchema), raw);
    },

    async getProducts(params: {
      category?: string;
      search?: string;
      page?: number;
      page_size?: number;
    } = {}): Promise<ProductsPage> {
      const raw = await fetcher<unknown>("/api/products/", { searchParams: params });
      return parse(ProductsPageSchema, raw);
    },

    async getProduct(slug: string): Promise<ProductDetail> {
      const raw = await fetcher<unknown>(`/api/products/${slug}/`);
      return parse(ProductDetailSchema, raw);
    },

    async getCart(): Promise<Cart> {
      const raw = await fetcher<unknown>("/api/cart/");
      return parse(CartSchema, raw);
    },

    async addCartItem(body: AddCartItemBody): Promise<Cart> {
      const raw = await fetcher<unknown>("/api/cart/items/", {
        method: "POST",
        body: JSON.stringify(body),
      });
      return parse(CartSchema, raw);
    },

    async updateCartItem(id: number, body: UpdateCartItemBody): Promise<Cart> {
      const raw = await fetcher<unknown>(`/api/cart/items/${id}/`, {
        method: "PATCH",
        body: JSON.stringify(body),
      });
      return parse(CartSchema, raw);
    },

    async removeCartItem(id: number): Promise<void> {
      await fetcher<void>(`/api/cart/items/${id}/`, { method: "DELETE" });
    },

    async clearCart(): Promise<void> {
      await fetcher<void>("/api/cart/", { method: "DELETE" });
    },

    async getPickupLocations(): Promise<PickupLocation[]> {
      const raw = await fetcher<unknown>("/api/pickup-locations/");
      return parse(z.array(PickupLocationSchema), raw);
    },

    async getFulfillmentOptions(type: FulfillmentType): Promise<FulfillmentOptions> {
      const raw = await fetcher<unknown>("/api/fulfillment-options/", {
        searchParams: { type },
      });
      return parse(FulfillmentOptionsSchema, raw);
    },

    async validatePromoCode(code: string): Promise<PromoValidation> {
      const raw = await fetcher<unknown>("/api/promo-codes/validate/", {
        method: "POST",
        body: JSON.stringify({ code }),
      });
      return parse(PromoValidationSchema, raw);
    },

    async previewOrder(body: PreviewOrderBody): Promise<OrderPreview> {
      const raw = await fetcher<unknown>("/api/orders/preview/", {
        method: "POST",
        body: JSON.stringify(body),
      });
      return parse(OrderPreviewSchema, raw);
    },

    async placeOrder(body: PlaceOrderBody): Promise<Order> {
      const raw = await fetcher<unknown>("/api/orders/", {
        method: "POST",
        body: JSON.stringify(body),
      });
      return parse(OrderSchema, raw);
    },

    async getOrder(number: string, token: string): Promise<Order> {
      const raw = await fetcher<unknown>(`/api/orders/${number}/`, {
        searchParams: { token },
      });
      return parse(OrderSchema, raw);
    },

    async startLibertyPayment(body: StartPaymentBody): Promise<StartPaymentResponse> {
      const raw = await fetcher<unknown>("/api/payments/liberty/start/", {
        method: "POST",
        body: JSON.stringify(body),
      });
      return parse(StartPaymentResponseSchema, raw);
    },

    async getLibertyPaymentEnabled(): Promise<{ enabled: boolean }> {
      return { enabled: true };
      const raw = await fetcher<unknown>("/api/payments/liberty/enabled/");
      return parse(LibertyPaymentEnabledSchema, raw);
    },

    async ensureCsrf(): Promise<void> {
      await fetcher<unknown>("/api/auth/csrf/");
    },

    async login(body: LoginBody): Promise<SessionUser> {
      const raw = await fetcher<unknown>("/api/auth/login/", {
        method: "POST",
        body: JSON.stringify(body),
      });
      return parse(SessionUserSchema, raw);
    },

    async logout(): Promise<void> {
      await fetcher<void>("/api/auth/logout/", { method: "POST" });
    },

    async getCurrentUser(): Promise<SessionUser> {
      const raw = await fetcher<unknown>("/api/auth/me/");
      return parse(SessionUserSchema, raw);
    },

    async markAttendance(eventType: AttendanceEventType): Promise<AttendanceEvent> {
      const raw = await fetcher<unknown>("/api/attendance/mark/", {
        method: "POST",
        body: JSON.stringify({ event_type: eventType }),
      });
      return parse(AttendanceEventSchema, raw);
    },

    async getAttendanceSummary(): Promise<AttendanceSummary> {
      const raw = await fetcher<unknown>("/api/attendance/summary/");
      return parse(AttendanceSummarySchema, raw);
    },
  };
}
