"use client";

import { useCan } from "@/hooks/useAuth";
import { formatAedWhole, sumCrmCakePrices } from "@/lib/format";
import { cn } from "@/lib/utils";

export function CrmProfitStats({
  orders,
  salary,
  rent,
  foodCost,
  compact,
}: {
  orders: { cake_price: string | null; delivery_price: string | null }[];
  salary: string | undefined;
  rent: string | undefined;
  foodCost: string | undefined;
  compact: boolean;
}) {
  const allowed = useCan("view_finance");
  if (!allowed) {
    return null;
  }
  if (salary === undefined || rent === undefined || foodCost === undefined) {
    return null;
  }

  return (
    <CrmProfitBadge
      orders={orders}
      salary={salary}
      rent={rent}
      foodCost={foodCost}
      compact={compact}
    />
  );
}

function CrmProfitBadge({
  orders,
  salary,
  rent,
  foodCost,
  compact,
}: {
  orders: { cake_price: string | null; delivery_price: string | null }[];
  salary: string;
  rent: string;
  foodCost: string;
  compact: boolean;
}) {
  const priced = orders.filter((order) => order.cake_price !== null && order.delivery_price !== null);
  if (orders.length > 0 && priced.length === 0) {
    return null;
  }
  const income = sumCrmCakePrices(priced);
  const expenses = Number.parseFloat(salary) + Number.parseFloat(rent) + Number.parseFloat(foodCost);
  const delta = income - expenses;

  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center rounded-lg border font-semibold tabular-nums",
        compact ? "px-1.5 py-0.5 text-xs" : "px-2.5 py-1 text-sm",
        delta < 0
          ? "border-red-200 bg-red-50 text-red-700"
          : "border-emerald-200 bg-emerald-50 text-emerald-700",
      )}
    >
      {formatSignedAedWhole(delta)}
    </span>
  );
}

function formatSignedAedWhole(value: number): string {
  const body = formatAedWhole(Math.abs(value));
  if (value < 0) {
    return `−${body}`;
  }
  return `+${body}`;
}
