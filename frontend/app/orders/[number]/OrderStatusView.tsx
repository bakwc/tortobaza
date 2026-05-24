"use client";

import { useEffect } from "react";
import { Check } from "lucide-react";
import { rememberOrder } from "@/lib/order-history";
import { formatAed, formatOrderTimeslot } from "@/lib/format";
import type { Order } from "@/lib/api/types";

const STATUS_LABEL: Record<string, string> = {
  pending: "Awaiting confirmation",
  confirmed: "Confirmed",
  preparing: "Being prepared",
  ready: "Ready",
  delivered: "Delivered",
  cancelled: "Cancelled",
};

const PAYMENT_LABEL: Record<string, string> = {
  card: "Card",
  cash: "Cash",
  bank_transfer: "Bank transfer",
};

const STATUS_TONE: Record<string, string> = {
  pending: "bg-amber-100 text-amber-900",
  confirmed: "bg-emerald-100 text-emerald-900",
  preparing: "bg-sky-100 text-sky-900",
  ready: "bg-emerald-100 text-emerald-900",
  delivered: "bg-emerald-100 text-emerald-900",
  cancelled: "bg-rose-100 text-rose-900",
};

export function OrderStatusView({ order }: { order: Order }) {
  useEffect(() => {
    rememberOrder(order.number, order.lookup_token);
  }, [order.number, order.lookup_token]);

  const tone = STATUS_TONE[order.status] ?? "bg-amber-100 text-amber-900";
  const label = STATUS_LABEL[order.status] ?? order.status;

  return (
    <div className="mt-6 space-y-6">
      <div className="rounded-3xl bg-white p-6 ring-1 ring-[var(--line)]">
        <div className="flex items-center gap-3">
          <span className="inline-flex h-12 w-12 items-center justify-center rounded-full bg-[var(--brand)] text-[var(--brand-foreground)]">
            <Check className="h-6 w-6" />
          </span>
          <div>
            <p className="text-sm text-[var(--ink)]/60">Order placed</p>
            <h1 className="font-display text-3xl">#{order.number}</h1>
          </div>
        </div>
        <span
          className={`mt-4 inline-flex rounded-full px-3 py-1 text-xs font-medium ${tone}`}
        >
          {label}
        </span>

        <dl className="mt-6 grid gap-4 text-sm sm:grid-cols-2">
          <Field label="Customer">
            {order.customer_name}
            <br />
            {order.customer_phone}
            {order.customer_email ? (
              <>
                <br />
                {order.customer_email}
              </>
            ) : null}
            {order.customer_instagram ? (
              <>
                <br />
                Instagram: {order.customer_instagram}
              </>
            ) : null}
            {order.customer_telegram ? (
              <>
                <br />
                Telegram: {order.customer_telegram}
              </>
            ) : null}
          </Field>
          <Field label="Fulfillment">
            {order.fulfillment_type === "delivery" ? "Delivery" : "Pickup"}
            {order.timeslot_start && order.timeslot_end ? (
              <>
                <br />
                {formatOrderTimeslot(order.timeslot_start, order.timeslot_end)}
              </>
            ) : null}
          </Field>
          {order.delivery_address ? (
            <Field label="Address">
              {order.delivery_address.building}, {order.delivery_address.street}
              {order.delivery_address.apartment
                ? `, ${order.delivery_address.apartment}`
                : ""}
              <br />
              {order.delivery_address.city}
              {order.delivery_address.postal_code
                ? `, ${order.delivery_address.postal_code}`
                : ""}
            </Field>
          ) : null}
          {order.pickup_location ? (
            <Field label="Pickup location">
              {order.pickup_location.name}
              <br />
              {order.pickup_location.address}
            </Field>
          ) : null}
          <Field label="Payment">
            {PAYMENT_LABEL[order.payment_method] ?? order.payment_method} ·{" "}
            <span className="text-[var(--ink)]/60">{order.payment_status}</span>
          </Field>
          {order.comment ? (
            <Field label="Comment">{order.comment}</Field>
          ) : null}
        </dl>
      </div>

      <div className="rounded-3xl bg-white p-6 ring-1 ring-[var(--line)]">
        <h2 className="font-display text-2xl">Items</h2>
        <ul className="mt-4 divide-y divide-[var(--line)]">
          {order.items.map((item) => (
            <li
              key={item.id}
              className="flex items-baseline justify-between py-3 text-sm"
            >
              <span className="pr-3">
                <span className="text-[var(--ink)]/60">x{item.quantity}</span>{" "}
                {item.product_name}
                {item.options.length > 0 ? (
                  <span className="block text-xs text-[var(--ink)]/60">
                    {item.options
                      .map((o) => `${o.group_name}: ${o.option_name}`)
                      .join(" · ")}
                  </span>
                ) : null}
              </span>
              <span className="font-medium tabular-nums">
                {formatAed(item.line_total)}
              </span>
            </li>
          ))}
        </ul>
        <dl className="mt-4 space-y-1 border-t border-[var(--line)] pt-4 text-sm">
          <Row label="Subtotal" value={formatAed(order.subtotal)} />
          {Number.parseFloat(order.discount_total) > 0 ? (
            <Row
              label="Discount"
              value={`−${formatAed(order.discount_total)}`}
              tone="text-[var(--brand)]"
            />
          ) : null}
          <Row label="Total" value={formatAed(order.total)} bold />
        </dl>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <dt className="text-xs font-medium uppercase tracking-wide text-[var(--ink)]/50">
        {label}
      </dt>
      <dd className="mt-1 leading-relaxed text-[var(--ink)]/80">{children}</dd>
    </div>
  );
}

function Row({
  label,
  value,
  tone,
  bold,
}: {
  label: string;
  value: string;
  tone?: string;
  bold?: boolean;
}) {
  return (
    <div className={`flex justify-between ${tone ?? ""} ${bold ? "text-base" : ""}`}>
      <dt className={bold ? "font-medium" : "text-[var(--ink)]/60"}>{label}</dt>
      <dd className={bold ? "font-semibold tabular-nums" : "tabular-nums"}>
        {value}
      </dd>
    </div>
  );
}
