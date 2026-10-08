"use client";

import { useLocale, useTranslations } from "next-intl";
import type { FinanceTransaction } from "@/lib/api/types";
import { formatAed, formatCrmCompactDate } from "@/lib/format";

const INCOME_TYPES = ["online", "terminal", "cash", "transfer"] as const;
const EXPENSE_TYPES = ["salary", "rent", "products", "consumables", "equipment"] as const;

function isIncomeType(value: string): value is (typeof INCOME_TYPES)[number] {
  return INCOME_TYPES.some((item) => item === value);
}

function isExpenseType(value: string): value is (typeof EXPENSE_TYPES)[number] {
  return EXPENSE_TYPES.some((item) => item === value);
}

export function FinanceTransactionList({ transactions }: { transactions: FinanceTransaction[] }) {
  const t = useTranslations("finance");
  const locale = useLocale();

  if (transactions.length === 0) {
    return (
      <div className="rounded-3xl border border-[var(--line)] bg-white p-8 text-center text-sm text-[var(--muted-2)] shadow-sm">
        {t("empty")}
      </div>
    );
  }

  return (
    <ul className="grid gap-3">
      {transactions.map((tx) => {
        const typeLabel = operationTypeLabel(tx, t);
        return (
          <li
            key={tx.id}
            className="rounded-3xl border border-[var(--line)] bg-white p-4 shadow-sm"
          >
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0">
                <div className="text-sm font-medium text-[var(--ink)]">
                  {formatCrmCompactDate(tx.date, locale)}
                </div>
                <div className="mt-1 text-sm text-[var(--muted-2)]">
                  {t(`kinds.${tx.kind}`)}
                  {" · "}
                  {tx.account.name}
                  {typeLabel ? ` · ${typeLabel}` : ""}
                </div>
                {tx.counterparty_name ? (
                  <div className="mt-2 text-sm text-[var(--ink)]">{tx.counterparty_name}</div>
                ) : null}
                {tx.description ? (
                  <div className="mt-1 text-sm text-[var(--muted-2)]">{tx.description}</div>
                ) : null}
              </div>
              <div className="shrink-0 text-sm font-semibold text-[var(--ink)]">
                {formatAed(tx.amount)}
              </div>
            </div>
          </li>
        );
      })}
    </ul>
  );
}

function operationTypeLabel(
  tx: FinanceTransaction,
  t: ReturnType<typeof useTranslations<"finance">>,
): string {
  if (tx.kind === "income" && tx.income_type) {
    if (isIncomeType(tx.income_type)) {
      return t(`incomeTypes.${tx.income_type}`);
    }
    return tx.income_type;
  }
  if (tx.kind === "expense" && tx.expense_type) {
    if (isExpenseType(tx.expense_type)) {
      return t(`expenseTypes.${tx.expense_type}`);
    }
    return tx.expense_type;
  }
  return "";
}
