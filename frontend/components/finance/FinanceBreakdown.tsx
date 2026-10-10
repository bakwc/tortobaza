"use client";

import type { ReactNode } from "react";
import { useTranslations } from "next-intl";
import type { FinanceTransaction } from "@/lib/api/types";
import { formatAed } from "@/lib/format";
import type { FinancePeriodMode } from "@/hooks/useFinancePeriod";

const INCOME_TYPES = ["online", "terminal", "cash", "transfer"] as const;
const EXPENSE_TYPES = ["salary", "rent", "products", "consumables", "equipment", "fees", "taxi", "gasoline", "marketing"] as const;

function isIncomeType(value: string): value is (typeof INCOME_TYPES)[number] {
  return INCOME_TYPES.some((item) => item === value);
}

function isExpenseType(value: string): value is (typeof EXPENSE_TYPES)[number] {
  return EXPENSE_TYPES.some((item) => item === value);
}

function monthDays(yyyyMm: string): string[] {
  const [yearStr, monthStr] = yyyyMm.split("-");
  const year = Number(yearStr);
  const month = Number(monthStr);
  const count = new Date(Date.UTC(year, month, 0)).getUTCDate();
  const days: string[] = [];
  for (let day = 1; day <= count; day += 1) {
    days.push(`${yyyyMm}-${String(day).padStart(2, "0")}`);
  }
  return days;
}

function magnitude(amount: string): number {
  return Math.abs(Number.parseFloat(amount));
}

export function FinanceBreakdown({
  transactions,
  mode,
  month,
  typeField,
}: {
  transactions: FinanceTransaction[];
  mode: FinancePeriodMode;
  month: string;
  typeField: "income_type" | "expense_type";
}) {
  const t = useTranslations("finance");

  if (transactions.length === 0) {
    return (
      <div className="rounded-3xl border border-[var(--line)] bg-white p-8 text-center text-sm text-[var(--muted-2)] shadow-sm">
        {t("empty")}
      </div>
    );
  }

  const total = transactions.reduce((sum, tx) => sum + magnitude(tx.amount), 0);
  const byAccount = group(transactions, (tx) => String(tx.account.id)).map((row) => ({
    key: row.key,
    label: transactions.find((tx) => String(tx.account.id) === row.key)?.account.name ?? row.key,
    amount: row.amount,
  }));
  const byType = group(transactions, (tx) => tx[typeField] || "unspecified").map((row) => ({
    key: row.key,
    label: typeLabel(typeField, row.key, t),
    amount: row.amount,
  }));
  const byCounterparty = group(transactions, (tx) => tx.counterparty_name || "unspecified")
    .slice(0, 8)
    .map((row) => ({
      key: row.key,
      label: row.key === "unspecified" ? t("unspecifiedCounterparty") : row.key,
      amount: row.amount,
    }));
  const byDay =
    mode === "month"
      ? monthDays(month).map((day) => ({
          date: day,
          amount: transactions
            .filter((tx) => tx.date === day)
            .reduce((sum, tx) => sum + magnitude(tx.amount), 0),
        }))
      : [];

  return (
    <div className="grid gap-4">
      <section className="rounded-3xl border border-[var(--line)] bg-white p-6 shadow-sm">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-[var(--ink)]/60">
          {t("total")}
        </h2>
        <p className="mt-2 text-3xl font-semibold text-[var(--ink)]">{formatAed(total)}</p>
      </section>
      <ChartCard title={t("byAccount")}>
        <BarList rows={byAccount} />
      </ChartCard>
      <ChartCard title={t("byType")}>
        <BarList rows={byType} />
      </ChartCard>
      <ChartCard title={t("byCounterparty")}>
        <BarList rows={byCounterparty} />
      </ChartCard>
      {mode === "month" ? (
        <ChartCard title={t("byDay")}>
          <DayColumns days={byDay} />
        </ChartCard>
      ) : null}
    </div>
  );
}

function ChartCard({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="rounded-3xl border border-[var(--line)] bg-white p-6 shadow-sm">
      <h2 className="text-xs font-semibold uppercase tracking-wide text-[var(--ink)]/60">{title}</h2>
      <div className="mt-4">{children}</div>
    </section>
  );
}

function BarList({ rows }: { rows: { key: string; label: string; amount: number }[] }) {
  const max = Math.max(...rows.map((row) => row.amount));
  return (
    <div className="grid gap-3">
      {rows.map((row) => (
        <div key={row.key}>
          <div className="flex items-baseline justify-between gap-3 text-sm">
            <span className="min-w-0 truncate text-[var(--ink)]">{row.label}</span>
            <span className="shrink-0 font-medium text-[var(--ink)]">{formatAed(row.amount)}</span>
          </div>
          <div className="mt-1 h-2 rounded-full bg-[var(--line)]">
            <div
              className="h-2 rounded-full bg-[var(--brand)]"
              style={{ width: max === 0 ? "0%" : `${(row.amount / max) * 100}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

function DayColumns({ days }: { days: { date: string; amount: number }[] }) {
  const max = Math.max(...days.map((day) => day.amount));
  return (
    <div className="flex items-end gap-1 overflow-x-auto">
      {days.map((day) => {
        const height = day.amount === 0 || max === 0 ? 0 : Math.max(4, (day.amount / max) * 112);
        return (
          <div key={day.date} className="flex w-6 shrink-0 flex-col items-center gap-1" title={formatAed(day.amount)}>
            <div className="flex h-28 w-full items-end rounded-t bg-[var(--cream)]">
              <div className="w-full rounded-t bg-[var(--brand)]" style={{ height }} />
            </div>
            <span className="text-[10px] text-[var(--muted-2)]">{Number(day.date.slice(8))}</span>
          </div>
        );
      })}
    </div>
  );
}

function group(
  transactions: FinanceTransaction[],
  keyOf: (tx: FinanceTransaction) => string,
): { key: string; amount: number }[] {
  const totals = new Map<string, number>();
  for (const tx of transactions) {
    const key = keyOf(tx);
    totals.set(key, (totals.get(key) ?? 0) + magnitude(tx.amount));
  }
  return [...totals.entries()]
    .map(([key, amount]) => ({ key, amount }))
    .sort((left, right) => right.amount - left.amount);
}

function typeLabel(
  typeField: "income_type" | "expense_type",
  value: string,
  t: ReturnType<typeof useTranslations<"finance">>,
): string {
  if (value === "unspecified") {
    return t("unspecified");
  }
  if (typeField === "income_type" && isIncomeType(value)) {
    return t(`incomeTypes.${value}`);
  }
  if (typeField === "expense_type" && isExpenseType(value)) {
    return t(`expenseTypes.${value}`);
  }
  return value;
}
