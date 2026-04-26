"use client";

import Link from "next/link";
import { ShoppingBag } from "lucide-react";
import { useCart } from "@/hooks/useCart";
import { formatAed } from "@/lib/format";

export function MobileCartBar() {
  const { data: cart } = useCart();
  const items = cart?.items ?? [];
  const count = items.reduce((sum, i) => sum + i.quantity, 0);

  if (count === 0) return null;

  return (
    <Link
      href="/checkout"
      className="flex items-center justify-between rounded-full bg-[var(--brand)] px-5 py-3 text-[var(--brand-foreground)] shadow-lg"
    >
      <span className="inline-flex items-center gap-2 text-sm font-medium">
        <span className="relative inline-flex">
          <ShoppingBag className="h-5 w-5" />
          <span className="absolute -right-2 -top-2 inline-flex h-5 min-w-[1.25rem] items-center justify-center rounded-full bg-white px-1 text-[10px] font-semibold text-[var(--brand)]">
            {count}
          </span>
        </span>
        View order
      </span>
      <span className="text-sm font-medium">{formatAed(cart?.subtotal ?? "0")}</span>
    </Link>
  );
}
