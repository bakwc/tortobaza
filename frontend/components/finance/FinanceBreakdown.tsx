"use client";

import type { ReactNode } from "react";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { usePathname, useRouter } from "@/i18n/navigation";
import type { FinanceTransaction } from "@/lib/api/types";
import { formatAed, toGel } from "@/lib/format";
import { cn } from "@/lib/utils";

const INCOME_TYPES = ["online", "terminal", "cash", "transfer"] as const;
const EXPENSE_TYPES = ["salary", "rent", "products", "consumables", "equipment", "fees", "taxi", "gasoline", "marketing"] as const;
const NEUTRAL_ACTIVE = "bg-[var(--ink)] text-white";
const INCOME_ACTIVE = "bg-emerald-600 text-white";
const EXPENSE_ACTIVE = "bg-rose-600 text-white";

function isIncomeType(value: string): value is (typeof INCOME_TYPES)[number] {
  return INCOME_TYPES.some((item) => item === value);
}

function isExpenseType(value: string): value is (typeof EXPENSE_TYPES)[number] {
  return EXPENSE_TYPES.some((item) => item === value);
}

function readAccountIds(values: string[]): number[] {
  const ids: number[] = [];
  for (const value of values) {
    const id = Number(value);
    if (Number.isInteger(id)) ids.push(id);
  }
  return ids;
}

function toggleValue<T>(current: readonly T[], value: T): T[] {
  if (current.includes(value)) return current.filter((item) => item !== value);
  return [...current, value];
}

function hrefWithParams(
  pathname: string,
  current: string,
  updates: { key: string; values: string[] }[],
): string {
  const params = new URLSearchParams(current);
  for (const update of updates) {
    params.delete(update.key);
    for (const value of update.values) {
      params.append(update.key, value);
    }
  }
  const query = params.toString();
  return query ? `${pathname}?${query}` : pathname;
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

function magnitude(tx: FinanceTransaction, rates: Record<string, string>): number {
  return Math.abs(toGel(tx.amount, tx.account.currency, rates));
}

export function FinanceBreakdown({
  transactions,
  month,
  typeField,
  rates,
}: {
  transactions: FinanceTransaction[];
  month: string;
  typeField: "income_type" | "expense_type";
  rates: Record<string, string>;
}) {
  const t = useTranslations("finance");
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const typeParam = typeField === "income_type" ? "income_type" : "expense_type";
  const accountFilters = readAccountIds(searchParams.getAll("account"));
  const typeFilters = searchParams.getAll(typeParam);
  const typeActiveClass = typeField === "income_type" ? INCOME_ACTIVE : EXPENSE_ACTIVE;

  function replaceFilters(next: { account: number[]; type: string[] }) {
    router.replace(
      hrefWithParams(pathname, searchParams.toString(), [
        { key: "account", values: next.account.map(String) },
        { key: typeParam, values: next.type },
      ]),
      { scroll: false },
    );
  }

  if (transactions.length === 0) {
    return (
      <div className="rounded-3xl border border-[var(--line)] bg-white p-8 text-center text-sm text-[var(--muted-2)] shadow-sm">
        {t("empty")}
      </div>
    );
  }

  const knownTypes = typeField === "income_type" ? INCOME_TYPES : EXPENSE_TYPES;
  const accounts = [
    ...new Map(transactions.map((tx) => [tx.account.id, tx.account.name])).entries(),
  ].sort((left, right) => left[1].localeCompare(right[1]));
  const types = knownTypes.filter((type) => transactions.some((tx) => tx[typeField] === type));
  const hasUnspecified = transactions.some((tx) => tx[typeField] === "");
  const visible = transactions.filter(
    (tx) =>
      (accountFilters.length === 0 || accountFilters.includes(tx.account.id)) &&
      (typeFilters.length === 0 || typeFilters.includes(tx[typeField])),
  );

  const total = visible.reduce((sum, tx) => sum + magnitude(tx, rates), 0);
  const byAccount = group(visible, (tx) => String(tx.account.id), rates).map((row) => ({
    key: row.key,
    label: visible.find((tx) => String(tx.account.id) === row.key)?.account.name ?? row.key,
    amount: row.amount,
  }));
  const byType = group(visible, (tx) => tx[typeField] || "unspecified", rates).map((row) => ({
    key: row.key,
    label: typeLabel(typeField, row.key, t),
    amount: row.amount,
  }));
  const counterparties = group(visible, (tx) => tx.counterparty_name || "unspecified", rates);
  const otherAmount = counterparties.slice(20).reduce((sum, row) => sum + row.amount, 0);
  const byCounterparty = counterparties.slice(0, 20).map((row) => ({
    key: row.key,
    label: row.key === "unspecified" ? t("unspecifiedCounterparty") : row.key,
    amount: row.amount,
  }));
  if (otherAmount > 0) {
    byCounterparty.push({
      key: "other",
      label: t("otherCounterparties"),
      amount: otherAmount,
    });
  }
  const byDay = monthDays(month).map((day) => ({
    date: day,
    amount: visible
      .filter((tx) => tx.date === day)
      .reduce((sum, tx) => sum + magnitude(tx, rates), 0),
  }));

  return (
    <div className="grid gap-4">
      <div className="grid gap-2 rounded-2xl border border-[var(--line)] bg-white px-3 py-2.5 shadow-sm">
        <FilterRow label={t("filterAccount")}>
          <FilterPill
            active={accountFilters.length === 0}
            activeClass={NEUTRAL_ACTIVE}
            onClick={() => replaceFilters({ account: [], type: typeFilters })}
          >
            {t("filterAll")}
          </FilterPill>
          {accounts.map(([id, name]) => (
            <FilterPill
              key={id}
              active={accountFilters.includes(id)}
              activeClass={NEUTRAL_ACTIVE}
              onClick={() => replaceFilters({ account: toggleValue(accountFilters, id), type: typeFilters })}
            >
              {name}
            </FilterPill>
          ))}
        </FilterRow>
        <FilterRow label={t(typeField === "income_type" ? "filterIncomeType" : "filterExpenseType")}>
          <FilterPill
            active={typeFilters.length === 0}
            activeClass={NEUTRAL_ACTIVE}
            onClick={() => replaceFilters({ account: accountFilters, type: [] })}
          >
            {t("filterAll")}
          </FilterPill>
          {types.map((type) => (
            <FilterPill
              key={type}
              active={typeFilters.includes(type)}
              activeClass={typeActiveClass}
              onClick={() => replaceFilters({ account: accountFilters, type: toggleValue(typeFilters, type) })}
            >
              {typeField === "income_type" ? t(`incomeTypes.${type}`) : t(`expenseTypes.${type}`)}
            </FilterPill>
          ))}
          {hasUnspecified ? (
            <FilterPill
              active={typeFilters.includes("")}
              activeClass={typeActiveClass}
              onClick={() => replaceFilters({ account: accountFilters, type: toggleValue(typeFilters, "") })}
            >
              {t("unspecified")}
            </FilterPill>
          ) : null}
        </FilterRow>
      </div>
      {visible.length === 0 ? (
        <div className="rounded-3xl border border-[var(--line)] bg-white p-8 text-center text-sm text-[var(--muted-2)] shadow-sm">
          {t("empty")}
        </div>
      ) : (
        <>
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
          <ChartCard title={t("byDay")}>
            <DayColumns days={byDay} />
          </ChartCard>
        </>
      )}
    </div>
  );
}

function FilterRow({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex min-w-0 flex-wrap items-center gap-1.5">
      <span className="mr-1 w-28 shrink-0 text-[10px] font-semibold uppercase tracking-wide text-[var(--muted-2)]">
        {label}
      </span>
      {children}
    </div>
  );
}

function FilterPill({
  active,
  activeClass,
  onClick,
  children,
}: {
  active: boolean;
  activeClass: string;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={onClick}
      className={cn(
        "flex items-center gap-1 rounded-full border px-2.5 py-1 text-xs font-semibold transition-colors [&_svg]:h-3 [&_svg]:w-3",
        active
          ? cn("border-transparent", activeClass)
          : "border-[var(--line)] bg-white text-[var(--ink)] hover:bg-[var(--cream-soft)]",
      )}
    >
      {children}
    </button>
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
  rates: Record<string, string>,
): { key: string; amount: number }[] {
  const totals = new Map<string, number>();
  for (const tx of transactions) {
    const key = keyOf(tx);
    totals.set(key, (totals.get(key) ?? 0) + magnitude(tx, rates));
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
