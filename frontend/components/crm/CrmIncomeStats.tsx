"use client";

import { useEffect, useRef, useState } from "react";
import { Info } from "lucide-react";
import { useTranslations } from "next-intl";
import { useCurrentUser } from "@/hooks/useAuth";
import { formatAed, sumCrmCakePrices } from "@/lib/format";
import { cn } from "@/lib/utils";

export function CrmIncomeStats({
  orders,
  compact,
}: {
  orders: { cake_price: string; is_paid: boolean }[];
  compact: boolean;
}) {
  const currentUser = useCurrentUser();
  if (!currentUser.data?.is_staff) {
    return null;
  }

  return <CrmIncomeBadge orders={orders} compact={compact} />;
}

function CrmIncomeBadge({
  orders,
  compact,
}: {
  orders: { cake_price: string; is_paid: boolean }[];
  compact: boolean;
}) {
  const t = useTranslations("crm");
  const [hintOpen, setHintOpen] = useState(false);
  const rootRef = useRef<HTMLSpanElement>(null);
  const income = sumCrmCakePrices(orders);
  const paid = sumCrmCakePrices(orders.filter((order) => order.is_paid));

  useEffect(() => {
    if (!hintOpen) {
      return;
    }
    const onPointerDown = (event: PointerEvent) => {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) {
        setHintOpen(false);
      }
    };
    document.addEventListener("pointerdown", onPointerDown);
    return () => document.removeEventListener("pointerdown", onPointerDown);
  }, [hintOpen]);

  const badge = (
    <span ref={rootRef} className="relative inline-flex">
      <span
        className={cn(
          "inline-flex shrink-0 items-center gap-1 rounded-lg border border-[var(--line)] bg-[var(--cream)] font-semibold tabular-nums text-[var(--ink)]",
          compact ? "px-1.5 py-0.5 text-xs" : "px-2.5 py-1 text-sm",
        )}
      >
        <span>{t("income")}</span>
        <span>
          {formatAed(income)} / {formatAed(paid)}
        </span>
        <button
          type="button"
          aria-label={t("incomeHint")}
          aria-expanded={hintOpen}
          className="inline-flex shrink-0 text-[var(--muted-2)]"
          onClick={(event) => {
            event.preventDefault();
            event.stopPropagation();
            setHintOpen((open) => !open);
          }}
          onPointerDown={(event) => {
            event.stopPropagation();
          }}
        >
          <Info className={compact ? "h-3 w-3" : "h-3.5 w-3.5"} />
        </button>
      </span>
      {hintOpen ? (
        <span
          className={cn(
            "absolute z-20 mt-1 w-56 rounded-lg border border-[var(--line)] bg-white px-2.5 py-2 text-left text-xs font-normal leading-snug text-[var(--ink)] shadow-md",
            compact ? "right-0 top-full" : "left-1/2 top-full -translate-x-1/2",
          )}
        >
          {t("incomeHint")}
        </span>
      ) : null}
    </span>
  );

  if (compact) {
    return badge;
  }

  return <div className="mt-3 flex justify-center">{badge}</div>;
}
