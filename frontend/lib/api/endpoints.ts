import { ApiError } from "./client";
import {
  AttendanceEventSchema,
  AttendanceSummarySchema,
  CartSchema,
  CategoryDetailSchema,
  CategoryLandingSchema,
  CategorySchema,
  CrmClientOrderSchema,
  CrmExpensesDaySchema,
  CrmExpensesMonthSchema,
  AnalyticsClientsSchema,
  AnalyticsLoadSchema,
  AnalyticsOverviewSchema,
  AnalyticsProductsSchema,
  CrmSalariesSchema,
  ExchangeRatesSchema,
  FinanceAccountSchema,
  FinanceTransactionSchema,
  FinanceTransactionSearchResultSchema,
  FinanceTransactionsResponseSchema,
  CrmMapOrdersResponseSchema,
  CrmMonthlyOrdersResponseSchema,
  CrmUnconfirmedOrdersResponseSchema,
  AuditEventsResponseSchema,
  CrmOrderEventSchema,
  CrmOrderSchema,
  CrmOrdersResponseSchema,
  ResolveGoogleAddressResponseSchema,
  ResolveYandexAddressResponseSchema,
  RsInvoiceSchema,
  RsgePendingCountSchema,
  RsWaybillSchema,
  WaybillSupplyDraftSchema,
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
  PayPalCaptureResponseSchema,
  PayPalConfigSchema,
  PayPalCreateResponseSchema,
  type AddCartItemBody,
  type AttendanceEvent,
  type AttendanceEventType,
  type AttendanceSummary,
  type Cart,
  type Category,
  type CategoryDetail,
  type CategoryLanding,
  type CrmClientOrder,
  type CrmExpensesDay,
  type CrmExpensesMonth,
  type AnalyticsClients,
  type AnalyticsLoad,
  type AnalyticsOverview,
  type AnalyticsProducts,
  type CrmSalaries,
  type ExchangeRates,
  type FinanceAccount,
  type FinanceTransaction,
  type FinanceTransactionSearchResult,
  type FinanceTransactionWriteBody,
  type FinanceTransactionsResponse,
  type CrmMapOrderRange,
  type CrmMapOrdersResponse,
  type CrmMonthlyOrdersResponse,
  type CrmUnconfirmedOrdersResponse,
  type CrmOrder,
  type AuditEventsResponse,
  type CrmOrderEvent,
  type CrmOrderItemCostBody,
  type CrmOrdersResponse,
  type ResolveGoogleAddressResponse,
  type ResolveYandexAddressResponse,
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
  type RsInvoice,
  type RsgePendingCount,
  type RsWaybill,
  type SessionUser,
  type StartPaymentBody,
  type StartPaymentResponse,
  type PayPalCaptureBody,
  type PayPalCaptureResponse,
  type PayPalConfig,
  type PayPalCreateBody,
  type PayPalCreateResponse,
  type UpdateCartItemBody,
  type UpdateCrmOrderBody,
  CatalogOptionSchema,
  IngredientCategorySchema,
  IngredientSchema,
  InventoryCountSchema,
  MenuImageSchema,
  MissingModifierLineSchema,
  FinishedGoodSchema,
  FinishedProductionSchema,
  ModifierGroupSchema,
  ProductionSchema,
  SemiProductSchema,
  StockMovementSchema,
  StockRowSchema,
  SupplierSchema,
  SupplyReceiptSchema,
  SupplySchema,
  SupplyTransactionSchema,
  TechCardCategorySchema,
  TechCardCostSchema,
  TechCardSchema,
  WriteOffReasonSchema,
  WriteOffSchema,
  type CatalogOption,
  type ComponentRefBody,
  type Ingredient,
  type IngredientBody,
  type IngredientCategory,
  type IngredientCategoryBody,
  type InventoryCount,
  type InventoryCountBody,
  type MenuImage,
  type MissingModifierLine,
  type ModifierGroup,
  type ModifierGroupBody,
  type FinishedGood,
  type FinishedProduction,
  type FinishedProductionBody,
  type Production,
  type ProductionBody,
  type SemiProduct,
  type SemiProductBody,
  type StockMovement,
  type StockRow,
  type Supplier,
  type SupplierBody,
  type Supply,
  type SupplyBody,
  type WaybillSupplyBody,
  type WaybillSupplyDraft,
  type SupplyReceipt,
  type SupplyTransaction,
  type TechCard,
  type TechCardBody,
  type TechCardCategory,
  type TechCardCategoryBody,
  type WriteOff,
  type WriteOffBody,
  type WriteOffReason,
  type WriteOffReasonBody,
} from "./types";
import { z } from "zod";

export type Fetcher = <T>(
  path: string,
  options?: {
    method?: string;
    body?: string | FormData;
    searchParams?: Record<string, string | number | undefined | null>;
    headers?: HeadersInit;
    signal?: AbortSignal;
    cache?: RequestCache;
    next?: { revalidate?: number; tags?: string[] };
  },
) => Promise<T>;

function parse<T>(schema: z.ZodType<T>, raw: unknown): T {
  return schema.parse(raw);
}

function resource<T, B>(fetcher: Fetcher, path: string, schema: z.ZodType<T>) {
  return {
    async list(): Promise<T[]> {
      const raw = await fetcher<unknown>(path);
      return parse(z.array(schema), raw);
    },
    async get(id: number): Promise<T> {
      const raw = await fetcher<unknown>(`${path}${id}/`);
      return parse(schema, raw);
    },
    async create(body: B): Promise<T> {
      const raw = await fetcher<unknown>(path, { method: "POST", body: JSON.stringify(body) });
      return parse(schema, raw);
    },
    async update(id: number, body: B): Promise<T> {
      const raw = await fetcher<unknown>(`${path}${id}/`, { method: "PUT", body: JSON.stringify(body) });
      return parse(schema, raw);
    },
    async remove(id: number): Promise<void> {
      await fetcher<void>(`${path}${id}/`, { method: "DELETE" });
    },
  };
}

export type Resource<T, B> = ReturnType<typeof resource<T, B>>;

export type FinanceScope = "business" | "personal";

export function endpoints(fetcher: Fetcher) {
  return {
    menuIngredientCategories: resource<IngredientCategory, IngredientCategoryBody>(
      fetcher,
      "/api/menu/ingredient-categories/",
      IngredientCategorySchema,
    ),
    menuIngredients: resource<Ingredient, IngredientBody>(fetcher, "/api/menu/ingredients/", IngredientSchema),
    assignIngredientCategory(ids: number[], category: number | null): Promise<void> {
      return fetcher<void>("/api/menu/ingredients/assign-category/", {
        method: "POST",
        body: JSON.stringify({ ids, category }),
      });
    },
    menuSemiProducts: resource<SemiProduct, SemiProductBody>(
      fetcher,
      "/api/menu/semi-products/",
      SemiProductSchema,
    ),
    menuModifierGroups: resource<ModifierGroup, ModifierGroupBody>(
      fetcher,
      "/api/menu/modifier-groups/",
      ModifierGroupSchema,
    ),
    menuTechCardCategories: resource<TechCardCategory, TechCardCategoryBody>(
      fetcher,
      "/api/menu/tech-card-categories/",
      TechCardCategorySchema,
    ),
    menuTechCards: resource<TechCard, TechCardBody>(fetcher, "/api/menu/tech-cards/", TechCardSchema),
    assignTechCardCategory(ids: number[], category: number | null): Promise<void> {
      return fetcher<void>("/api/menu/tech-cards/assign-category/", {
        method: "POST",
        body: JSON.stringify({ ids, category }),
      });
    },
    inventorySuppliers: resource<Supplier, SupplierBody>(fetcher, "/api/inventory/suppliers/", SupplierSchema),
    inventorySupplies: resource<Supply, SupplyBody>(fetcher, "/api/inventory/supplies/", SupplySchema),
    inventoryProductions: resource<Production, ProductionBody>(
      fetcher,
      "/api/inventory/productions/",
      ProductionSchema,
    ),
    inventoryFinishedProductions: resource<FinishedProduction, FinishedProductionBody>(
      fetcher,
      "/api/inventory/finished-productions/",
      FinishedProductionSchema,
    ),
    inventoryFinishedGoods: resource<FinishedGood, never>(
      fetcher,
      "/api/inventory/finished-goods/",
      FinishedGoodSchema,
    ),
    inventoryWriteOffReasons: resource<WriteOffReason, WriteOffReasonBody>(
      fetcher,
      "/api/inventory/write-off-reasons/",
      WriteOffReasonSchema,
    ),
    inventoryWriteOffs: resource<WriteOff, WriteOffBody>(fetcher, "/api/inventory/write-offs/", WriteOffSchema),
    inventoryCounts: resource<InventoryCount, InventoryCountBody>(
      fetcher,
      "/api/inventory/inventory-counts/",
      InventoryCountSchema,
    ),
    async getRsgeWaybills(month: string): Promise<RsWaybill[]> {
      const raw = await fetcher<unknown>("/api/rsge/waybills/", { searchParams: { month } });
      return parse(z.array(RsWaybillSchema), raw);
    },

    async confirmRsgeWaybill(id: number): Promise<RsWaybill> {
      const raw = await fetcher<unknown>(`/api/rsge/waybills/${id}/confirm/`, { method: "POST" });
      return parse(RsWaybillSchema, raw);
    },

    async rejectRsgeWaybill(id: number): Promise<RsWaybill> {
      const raw = await fetcher<unknown>(`/api/rsge/waybills/${id}/reject/`, { method: "POST" });
      return parse(RsWaybillSchema, raw);
    },

    async waybillSupplyDraft(id: number): Promise<WaybillSupplyDraft> {
      const raw = await fetcher<unknown>(`/api/rsge/waybills/${id}/supply-draft/`, { method: "POST" });
      return parse(WaybillSupplyDraftSchema, raw);
    },

    async createWaybillSupply(id: number, body: WaybillSupplyBody): Promise<Supply> {
      const raw = await fetcher<unknown>(`/api/rsge/waybills/${id}/supply/`, {
        method: "POST",
        body: JSON.stringify(body),
      });
      return parse(SupplySchema, raw);
    },

    async getRsgeInvoices(month: string): Promise<RsInvoice[]> {
      const raw = await fetcher<unknown>("/api/rsge/invoices/", { searchParams: { month } });
      return parse(z.array(RsInvoiceSchema), raw);
    },

    async confirmRsgeInvoice(id: number): Promise<RsInvoice> {
      const raw = await fetcher<unknown>(`/api/rsge/invoices/${id}/confirm/`, { method: "POST" });
      return parse(RsInvoiceSchema, raw);
    },

    async rejectRsgeInvoice(id: number, refText: string): Promise<RsInvoice> {
      const raw = await fetcher<unknown>(`/api/rsge/invoices/${id}/reject/`, {
        method: "POST",
        body: JSON.stringify({ ref_text: refText }),
      });
      return parse(RsInvoiceSchema, raw);
    },

    async getRsgePendingCount(): Promise<RsgePendingCount> {
      const raw = await fetcher<unknown>("/api/rsge/pending-count/");
      return parse(RsgePendingCountSchema, raw);
    },

    async getTechCardCost(
      id: number,
      weightKg: string | null,
      modifiers: { modifier: number; quantity: number }[],
    ): Promise<string> {
      const raw = await fetcher<unknown>(`/api/menu/tech-cards/${id}/cost/`, {
        searchParams: {
          weight_kg: weightKg,
          modifiers: modifiers.map((row) => `${row.modifier}:${row.quantity}`).join(","),
        },
      });
      return parse(TechCardCostSchema, raw).cost;
    },

    async uploadTechCardImage(id: number, file: File): Promise<MenuImage> {
      const body = new FormData();
      body.append("image", file);
      const raw = await fetcher<unknown>(`/api/menu/tech-cards/${id}/images/`, { method: "POST", body });
      return parse(MenuImageSchema, raw);
    },

    async deleteTechCardImage(id: number, imageId: number): Promise<void> {
      await fetcher<void>(`/api/menu/tech-cards/${id}/images/${imageId}/`, { method: "DELETE" });
    },

    async uploadSemiProductImage(id: number, file: File): Promise<MenuImage> {
      const body = new FormData();
      body.append("image", file);
      const raw = await fetcher<unknown>(`/api/menu/semi-products/${id}/images/`, { method: "POST", body });
      return parse(MenuImageSchema, raw);
    },

    async deleteSemiProductImage(id: number, imageId: number): Promise<void> {
      await fetcher<void>(`/api/menu/semi-products/${id}/images/${imageId}/`, { method: "DELETE" });
    },

    async getMissingModifierLines(): Promise<MissingModifierLine[]> {
      const raw = await fetcher<unknown>("/api/menu/missing-modifier-lines/");
      return parse(z.array(MissingModifierLineSchema), raw);
    },

    async getCatalogOptions(): Promise<CatalogOption[]> {
      const raw = await fetcher<unknown>("/api/menu/catalog-options/");
      return parse(z.array(CatalogOptionSchema), raw);
    },

    async uploadSupplyReceipt(file: File): Promise<SupplyReceipt> {
      const body = new FormData();
      body.append("image", file);
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 100_000);
      try {
        const raw = await fetcher<unknown>("/api/inventory/receipts/", {
          method: "POST",
          body,
          signal: controller.signal,
        });
        return parse(SupplyReceiptSchema, raw);
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") {
          throw new ApiError(0, JSON.stringify({ detail: "Receipt recognition timed out." }));
        }
        throw error;
      } finally {
        clearTimeout(timer);
      }
    },

    async getStock(date: string | null): Promise<StockRow[]> {
      const raw = await fetcher<unknown>("/api/inventory/stock/", { searchParams: { date } });
      return parse(z.array(StockRowSchema), raw);
    },

    async getStockMovements(
      component: ComponentRefBody & { finished_good: number | null },
    ): Promise<StockMovement[]> {
      const raw = await fetcher<unknown>("/api/inventory/movements/", { searchParams: component });
      return parse(z.array(StockMovementSchema), raw);
    },

    async getSupplyTransactions(supplyId: number | null): Promise<SupplyTransaction[]> {
      const raw = await fetcher<unknown>("/api/inventory/supply-transactions/", {
        searchParams: { supply: supplyId },
      });
      return parse(z.array(SupplyTransactionSchema), raw);
    },

    async closeInventoryCount(id: number): Promise<InventoryCount> {
      const raw = await fetcher<unknown>(`/api/inventory/inventory-counts/${id}/close/`, { method: "POST" });
      return parse(InventoryCountSchema, raw);
    },

    async getCategories(): Promise<Category[]> {
      const raw = await fetcher<unknown>("/api/categories/");
      return parse(z.array(CategorySchema), raw);
    },

    async getCategoryLandings(locale?: string): Promise<CategoryLanding[]> {
      const raw = await fetcher<unknown>("/api/category-landings/", {
        headers: locale ? { "Accept-Language": locale } : undefined,
      });
      return parse(z.array(CategoryLandingSchema), raw);
    },

    async getCategory(pageSlug: string, locale: string): Promise<CategoryDetail> {
      const raw = await fetcher<unknown>(`/api/categories/${pageSlug}/`, {
        headers: { "Accept-Language": locale },
      });
      return parse(CategoryDetailSchema, raw);
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

    async getPayPalConfig(): Promise<PayPalConfig> {
      const raw = await fetcher<unknown>("/api/payments/paypal/config/");
      return parse(PayPalConfigSchema, raw);
    },

    async createPayPalOrder(body: PayPalCreateBody): Promise<PayPalCreateResponse> {
      const raw = await fetcher<unknown>("/api/payments/paypal/create/", {
        method: "POST",
        body: JSON.stringify(body),
      });
      return parse(PayPalCreateResponseSchema, raw);
    },

    async capturePayPalOrder(body: PayPalCaptureBody): Promise<PayPalCaptureResponse> {
      const raw = await fetcher<unknown>("/api/payments/paypal/capture/", {
        method: "POST",
        body: JSON.stringify(body),
      });
      return parse(PayPalCaptureResponseSchema, raw);
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

    async getCrmExpenses(date?: string): Promise<CrmExpensesDay> {
      const raw = await fetcher<unknown>("/api/crm/expenses/", {
        searchParams: date ? { date } : undefined,
      });
      return parse(CrmExpensesDaySchema, raw);
    },

    async getCrmExpensesByMonth(month: string): Promise<CrmExpensesMonth> {
      const raw = await fetcher<unknown>("/api/crm/expenses/", {
        searchParams: { month },
      });
      return parse(CrmExpensesMonthSchema, raw);
    },

    async getCrmSalaries(month: string): Promise<CrmSalaries> {
      const raw = await fetcher<unknown>("/api/crm/salaries/", {
        searchParams: { month },
      });
      return parse(CrmSalariesSchema, raw);
    },

    async getAnalyticsOverview(): Promise<AnalyticsOverview> {
      const raw = await fetcher<unknown>("/api/crm/analytics/overview/");
      return parse(AnalyticsOverviewSchema, raw);
    },

    async getAnalyticsLoad(month: string): Promise<AnalyticsLoad> {
      const raw = await fetcher<unknown>("/api/crm/analytics/load/", {
        searchParams: { month },
      });
      return parse(AnalyticsLoadSchema, raw);
    },

    async getAnalyticsClients(): Promise<AnalyticsClients> {
      const raw = await fetcher<unknown>("/api/crm/analytics/clients/");
      return parse(AnalyticsClientsSchema, raw);
    },

    async getAnalyticsProducts(month: string): Promise<AnalyticsProducts> {
      const raw = await fetcher<unknown>("/api/crm/analytics/products/", {
        searchParams: { month },
      });
      return parse(AnalyticsProductsSchema, raw);
    },

    async getFinanceTransactions(
      date: string,
      scope: FinanceScope,
    ): Promise<FinanceTransactionsResponse> {
      const raw = await fetcher<unknown>("/api/crm/finance/transactions/", {
        searchParams: { date, scope },
      });
      return parse(FinanceTransactionsResponseSchema, raw);
    },

    async getFinanceTransactionsByMonth(
      month: string,
      scope: FinanceScope,
    ): Promise<FinanceTransactionsResponse> {
      const raw = await fetcher<unknown>("/api/crm/finance/transactions/", {
        searchParams: { month, scope },
      });
      return parse(FinanceTransactionsResponseSchema, raw);
    },

    async getFinanceTransactionsByRange(
      start: string,
      end: string,
      scope: FinanceScope,
    ): Promise<FinanceTransactionsResponse> {
      const raw = await fetcher<unknown>("/api/crm/finance/transactions/", {
        searchParams: { start, end, scope },
      });
      return parse(FinanceTransactionsResponseSchema, raw);
    },

    async getFinanceAccounts(scope: FinanceScope): Promise<FinanceAccount[]> {
      const raw = await fetcher<unknown>("/api/crm/finance/accounts/", {
        searchParams: { scope },
      });
      return parse(z.array(FinanceAccountSchema), raw);
    },

    async searchFinanceTransactions(
      q: string,
      scope: FinanceScope,
    ): Promise<FinanceTransactionSearchResult[]> {
      const raw = await fetcher<unknown>("/api/crm/finance/transactions/search/", {
        searchParams: { q, scope },
      });
      return parse(z.array(FinanceTransactionSearchResultSchema), raw);
    },

    async createFinanceTransaction(
      body: FinanceTransactionWriteBody,
      scope: FinanceScope,
    ): Promise<FinanceTransaction> {
      const raw = await fetcher<unknown>("/api/crm/finance/transactions/", {
        method: "POST",
        searchParams: { scope },
        body: JSON.stringify(body),
      });
      return parse(FinanceTransactionSchema, raw);
    },

    async updateFinanceTransaction(
      id: number,
      body: FinanceTransactionWriteBody,
      scope: FinanceScope,
    ): Promise<FinanceTransaction> {
      const raw = await fetcher<unknown>(`/api/crm/finance/transactions/${id}/`, {
        method: "PUT",
        searchParams: { scope },
        body: JSON.stringify(body),
      });
      return parse(FinanceTransactionSchema, raw);
    },

    async deleteFinanceTransaction(id: number, scope: FinanceScope): Promise<void> {
      await fetcher<void>(`/api/crm/finance/transactions/${id}/`, {
        method: "DELETE",
        searchParams: { scope },
      });
    },

    async getExchangeRates(): Promise<ExchangeRates> {
      const raw = await fetcher<unknown>("/api/crm/finance/exchange-rates/");
      return parse(ExchangeRatesSchema, raw);
    },

    async getCrmOrderItemCost(body: CrmOrderItemCostBody): Promise<string> {
      const raw = await fetcher<unknown>("/api/crm/order-item-cost/", {
        method: "POST",
        body: JSON.stringify(body),
      });
      return parse(TechCardCostSchema, raw).cost;
    },

    async getCrmOrders(date?: string): Promise<CrmOrdersResponse> {
      const raw = await fetcher<unknown>("/api/crm/orders/", {
        searchParams: date ? { date } : undefined,
      });
      return parse(CrmOrdersResponseSchema, raw);
    },

    async getCrmOrdersByMonth(month: string): Promise<CrmMonthlyOrdersResponse> {
      const raw = await fetcher<unknown>("/api/crm/orders/", {
        searchParams: { month },
      });
      return parse(CrmMonthlyOrdersResponseSchema, raw);
    },

    async getCrmUnconfirmedOrders(): Promise<CrmUnconfirmedOrdersResponse> {
      const raw = await fetcher<unknown>("/api/crm/orders/", {
        searchParams: { status: "unconfirmed" },
      });
      return parse(CrmUnconfirmedOrdersResponseSchema, raw);
    },

    async getCrmMapOrders(
      range: CrmMapOrderRange | null,
      date: string | null,
    ): Promise<CrmMapOrdersResponse> {
      const raw = await fetcher<unknown>("/api/crm/orders/map/", {
        searchParams: date !== null ? { date } : { range },
      });
      return parse(CrmMapOrdersResponseSchema, raw);
    },

    async patchCrmOrder(id: number, body: UpdateCrmOrderBody): Promise<CrmOrder> {
      const raw = await fetcher<unknown>(`/api/crm/orders/${id}/`, {
        method: "PATCH",
        body: JSON.stringify(body),
      });
      return parse(CrmOrderSchema, raw);
    },

    async createCrmPaymentLink(id: number): Promise<CrmOrder> {
      const raw = await fetcher<unknown>(`/api/crm/orders/${id}/payment-link/`, {
        method: "POST",
      });
      return parse(CrmOrderSchema, raw);
    },

    async getCrmOrder(id: number): Promise<CrmOrder> {
      const raw = await fetcher<unknown>(`/api/crm/orders/${id}/`);
      return parse(CrmOrderSchema, raw);
    },

    async getAuditEvents(params: {
      page: number;
      start: string;
      end: string;
      app: string;
      q: string;
      model: string | null;
      objectId: string | null;
    }): Promise<AuditEventsResponse> {
      const raw = await fetcher<unknown>("/api/audit/events/", {
        searchParams: {
          page: params.page,
          start: params.start || undefined,
          end: params.end || undefined,
          app: params.app || undefined,
          q: params.q || undefined,
          model: params.model || undefined,
          object_id: params.objectId || undefined,
        },
      });
      return parse(AuditEventsResponseSchema, raw);
    },

    async getCrmOrderEvents(id: number): Promise<CrmOrderEvent[]> {
      const raw = await fetcher<unknown>(`/api/crm/orders/${id}/events/`);
      return parse(z.array(CrmOrderEventSchema), raw);
    },

    async getCrmClientOrder(token: string): Promise<CrmClientOrder> {
      const raw = await fetcher<unknown>(`/api/crm/orders/client/${token}/`);
      return parse(CrmClientOrderSchema, raw);
    },

    async getCrmClientOrderMap(token: string): Promise<ResolveGoogleAddressResponse> {
      const raw = await fetcher<unknown>(`/api/crm/orders/client/${token}/map/`);
      return parse(ResolveGoogleAddressResponseSchema, raw);
    },

    async createCrmOrder(body: FormData): Promise<CrmOrder> {
      const raw = await fetcher<unknown>("/api/crm/orders/", {
        method: "POST",
        body,
      });
      return parse(CrmOrderSchema, raw);
    },

    async updateCrmOrder(id: number, body: FormData): Promise<CrmOrder> {
      const raw = await fetcher<unknown>(`/api/crm/orders/${id}/`, {
        method: "PUT",
        body,
      });
      return parse(CrmOrderSchema, raw);
    },

    async deleteCrmOrder(id: number): Promise<void> {
      await fetcher<void>(`/api/crm/orders/${id}/`, { method: "DELETE" });
    },

    async resolveYandexAddress(address: string): Promise<ResolveYandexAddressResponse> {
      const raw = await fetcher<unknown>("/api/crm/resolve-yandex-address/", {
        method: "POST",
        body: JSON.stringify({ address }),
      });
      return parse(ResolveYandexAddressResponseSchema, raw);
    },

    async resolveGoogleAddress(address: string): Promise<ResolveGoogleAddressResponse> {
      const raw = await fetcher<unknown>("/api/crm/resolve-google-address/", {
        method: "POST",
        body: JSON.stringify({ address }),
      });
      return parse(ResolveGoogleAddressResponseSchema, raw);
    },
  };
}
