"use client";

import { useTranslations } from "next-intl";
import { useCurrentUser } from "@/hooks/useAuth";
import { formatAed } from "@/lib/format";
import { cn } from "@/lib/utils";

export function CrmExpenseStats({
  salary,
  compact,
}: {
  salary: string | undefined;
  compact: boolean;
}) {
  const currentUser = useCurrentUser();
  if (!currentUser.data?.is_staff) {
    return null;
  }
  if (salary === undefined) {
    return null;
  }

  return <CrmExpenseBadge salary={salary} compact={compact} />;
}

function CrmExpenseBadge({
  salary,
  compact,
}: {
  salary: string;
  compact: boolean;
}) {
  const t = useTranslations("crm");

  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center gap-1 rounded-lg border border-[var(--line)] bg-[var(--cream)] font-semibold tabular-nums text-[var(--ink)]",
        compact ? "px-1.5 py-0.5 text-xs" : "px-2.5 py-1 text-sm",
      )}
    >
      <span>{t("expenses")}</span>
      <span>
        {t("expensesSalary")} {formatAed(salary)}
      </span>
    </span>
  );
}
