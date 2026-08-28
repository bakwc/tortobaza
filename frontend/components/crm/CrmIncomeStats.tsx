"use client";

import { Banknote, CreditCard } from "lucide-react";
import { useTranslations } from "next-intl";
import { useCurrentUser } from "@/hooks/useAuth";
import { formatAed, sumCrmCakePrices } from "@/lib/format";

export function CrmIncomeStats({
  orders,
  compact,
}: {
  orders: { cake_price: string; is_paid: boolean }[];
  compact: boolean;
}) {
  const t = useTranslations("crm");
  const currentUser = useCurrentUser();
  if (!currentUser.data?.is_staff) {
    return null;
  }

  const income = sumCrmCakePrices(orders);
  const paidAmount = sumCrmCakePrices(orders.filter((order) => order.is_paid));

  if (compact) {
    return (
      <span className="shrink-0 text-xs font-medium text-[var(--muted-2)]">
        {formatAed(income)}
        <span className="mx-1">·</span>
        {t("paidAmount")} {formatAed(paidAmount)}
      </span>
    );
  }

  return (
    <div className="mt-3 flex flex-wrap items-center justify-center gap-3 text-xs sm:gap-6 sm:text-sm">
      <div className="flex items-center gap-1.5 text-[var(--ink)]">
        <Banknote className="h-4 w-4 text-[var(--muted-2)]" />
        <span>{t("income")}</span>
        <span className="font-bold">{formatAed(income)}</span>
      </div>
      <div className="flex items-center gap-1.5 text-emerald-700">
        <CreditCard className="h-4 w-4" />
        <span>{t("paidAmount")}</span>
        <span className="font-bold">{formatAed(paidAmount)}</span>
      </div>
    </div>
  );
}
