"use client";

import { useCart } from "@/hooks/useCart";
import { formatAed } from "@/lib/format";

export function CheckoutBasket() {
  const { data: cart } = useCart();
  const items = cart?.items ?? [];

  return (
    <aside className="rounded-3xl bg-white p-6 ring-1 ring-[var(--line)]">
      <h2 className="font-display text-2xl">Basket</h2>
      <ul className="mt-4 space-y-3">
        {items.map((item) => (
          <li key={item.id} className="flex items-baseline justify-between text-sm">
            <span className="truncate pr-2">
              <span className="text-[var(--ink)]/60">x{item.quantity}</span>{" "}
              {item.product.name}
            </span>
            <span className="font-medium tabular-nums">
              {formatAed(item.line_total)}
            </span>
          </li>
        ))}
      </ul>
      <div className="mt-4 border-t border-[var(--line)] pt-4 text-sm">
        <div className="flex justify-between">
          <span className="text-[var(--ink)]/60">Subtotal</span>
          <span className="font-medium">{formatAed(cart?.subtotal ?? "0")}</span>
        </div>
      </div>
    </aside>
  );
}
