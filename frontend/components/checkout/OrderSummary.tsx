"use client";

import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { Spinner } from "@/components/ui/spinner";
import { Button } from "@/components/ui/button";
import { useCart } from "@/hooks/useCart";
import { api } from "@/lib/api";
import { formatAed } from "@/lib/format";
import type { FulfillmentType } from "@/lib/api/types";

export function OrderSummary({
  fulfillmentType,
  promoCode,
  onPlaceOrder,
  isPlacing,
  canPlace,
  placeOrderLabel,
}: {
  fulfillmentType: FulfillmentType;
  promoCode: string;
  onPlaceOrder: () => void;
  isPlacing: boolean;
  canPlace: boolean;
  placeOrderLabel: string;
}) {
  const t = useTranslations("checkout");
  const { data: cart } = useCart();

  const { data: preview, isLoading } = useQuery({
    queryKey: ["order-preview", fulfillmentType, promoCode, cart?.subtotal],
    queryFn: () =>
      api.previewOrder({
        fulfillment_type: fulfillmentType,
        promo_code: promoCode || undefined,
      }),
    enabled: Boolean(cart && cart.items.length > 0),
  });

  const items = cart?.items ?? [];

  return (
    <aside className="sticky top-24 rounded-3xl bg-white p-6 ring-1 ring-[var(--line)]">
      <h2 className="font-display text-2xl">{t("basketSidebar")}</h2>
      <ul className="mt-4 space-y-3 text-sm">
        {items.map((item) => (
          <li key={item.id} className="flex items-baseline justify-between">
            <span className="truncate pr-2">
              <span className="text-[var(--ink)]/60">x{item.quantity}</span> {item.product.name}
            </span>
            <span className="font-medium tabular-nums">{formatAed(item.line_total)}</span>
          </li>
        ))}
      </ul>

      <dl className="mt-6 space-y-2 border-t border-[var(--line)] pt-4 text-sm">
        <div className="flex justify-between">
          <dt className="text-[var(--ink)]/60">{t("subtotal")}</dt>
          <dd className="font-medium tabular-nums">
            {formatAed(preview?.subtotal ?? cart?.subtotal ?? "0")}
          </dd>
        </div>
        {preview && Number.parseFloat(preview.discount_total) > 0 ? (
          <div className="flex justify-between text-[var(--brand)]">
            <dt>{t("discount")}</dt>
            <dd className="font-medium tabular-nums">
              −{formatAed(preview.discount_total)}
            </dd>
          </div>
        ) : null}
        {preview && Number.parseFloat(preview.delivery_fee) > 0 ? (
          <div className="flex justify-between">
            <dt className="text-[var(--ink)]/60">{t("deliveryFee")}</dt>
            <dd className="font-medium tabular-nums">{formatAed(preview.delivery_fee)}</dd>
          </div>
        ) : null}
        <div className="flex justify-between border-t border-[var(--line)] pt-2 text-base">
          <dt className="font-medium">{t("total")}</dt>
          <dd className="font-semibold tabular-nums">
            {isLoading ? <Spinner /> : formatAed(preview?.total ?? cart?.subtotal ?? "0")}
          </dd>
        </div>
      </dl>

      <Button
        type="button"
        size="lg"
        className="mt-6 w-full"
        onClick={onPlaceOrder}
        disabled={!canPlace || isPlacing}
      >
        {isPlacing ? <Spinner className="mr-2" /> : null}
        {placeOrderLabel}
      </Button>
    </aside>
  );
}
