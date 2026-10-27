"use client";

import { useLocale, useTranslations } from "next-intl";
import { ChevronRight, WalletCards } from "lucide-react";
import { Link } from "@/i18n/navigation";
import { useFinanceScope } from "@/hooks/useFinanceScope";
import { useFinanceTransactionsRange } from "@/hooks/useFinanceTransactions";
import type { FinanceTransaction } from "@/lib/api/types";
import { formatAed, getTbilisiTodayIsoDate, toGel } from "@/lib/format";

type AccountSummary = {
  id: number;
  name: string;
  plusCents: number;
  minusCents: number;
  deltaCents: number;
};

const SPEND_WINDOWS = [7, 30, 60] as const;

type SpendWindow = (typeof SPEND_WINDOWS)[number];

function gelCents(tx: FinanceTransaction, rates: Record<string, string>): number {
  return Math.round(toGel(tx.amount, tx.account.currency, rates) * 100);
}

function isoDateMinusDays(iso: string, days: number): string {
  const [year, month, day] = iso.split("-").map(Number);
  const date = new Date(Date.UTC(year, month - 1, day));
  date.setUTCDate(date.getUTCDate() - days);
  return date.toISOString().slice(0, 10);
}

function spendByAccount(
  transactions: FinanceTransaction[],
  rates: Record<string, string>,
  today: string,
): Map<number, Record<SpendWindow, number>> {
  const cuts: Record<SpendWindow, string> = {
    7: isoDateMinusDays(today, 7),
    30: isoDateMinusDays(today, 30),
    60: isoDateMinusDays(today, 60),
  };
  const byId = new Map<number, Record<SpendWindow, number>>();
  for (const tx of transactions) {
    const cents = gelCents(tx, rates);
    if (cents >= 0) continue;
    const spent = -cents;
    const row = byId.get(tx.account.id) ?? { 7: 0, 30: 0, 60: 0 };
    if (tx.date >= cuts[60]) row[60] += spent;
    if (tx.date >= cuts[30]) row[30] += spent;
    if (tx.date >= cuts[7]) row[7] += spent;
    byId.set(tx.account.id, row);
  }
  return byId;
}

function summarize(transactions: FinanceTransaction[], rates: Record<string, string>): AccountSummary[] {
  const byId = new Map<number, AccountSummary>();
  for (const tx of transactions) {
    const cents = gelCents(tx, rates);
    const existing = byId.get(tx.account.id);
    const row = existing ?? {
      id: tx.account.id,
      name: tx.account.name,
      plusCents: 0,
      minusCents: 0,
      deltaCents: 0,
    };
    if (cents > 0) {
      row.plusCents += cents;
    }
    if (cents < 0) {
      row.minusCents += cents;
    }
    row.deltaCents += cents;
    if (!existing) byId.set(tx.account.id, row);
  }
  return [...byId.values()];
}

export function FinanceAccountList({
  transactions,
  periodQuery,
  rates,
}: {
  transactions: FinanceTransaction[];
  periodQuery: string;
  rates: Record<string, string>;
}) {
  const t = useTranslations("finance");
  const locale = useLocale();
  const { scope } = useFinanceScope();
  const today = getTbilisiTodayIsoDate();
  const range = useFinanceTransactionsRange(isoDateMinusDays(today, 60), today, scope);

  if (transactions.length === 0) {
    return (
      <>
        {range.isError ? <p className="text-sm text-[var(--danger)]">{t("loadError")}</p> : null}
        <div className="rounded-3xl border border-[var(--line)] bg-white p-8 text-center text-sm text-[var(--muted-2)] shadow-sm">
          {t("empty")}
        </div>
      </>
    );
  }

  const accounts = summarize(transactions, rates).sort((a, b) => a.name.localeCompare(b.name, locale));
  const spend = range.data ? spendByAccount(range.data.transactions, rates, today) : null;

  return (
    <div className="grid gap-2">
      {range.isError ? <p className="text-sm text-[var(--danger)]">{t("loadError")}</p> : null}
      {accounts.map((account) => {
        const delta = account.deltaCents / 100;
        const deltaClass =
          delta > 0 ? "text-emerald-700" : delta < 0 ? "text-rose-700" : "text-[var(--ink)]";
        const formatted = formatAed(delta);
        const deltaLabel = delta > 0 ? `+${formatted}` : formatted;
        return (
          <Link
            key={account.id}
            href={`/finance?${periodQuery}&account=${account.id}`}
            className="flex min-w-0 items-center gap-2 rounded-xl border border-[var(--line)] bg-white px-2 py-2 shadow-sm transition hover:brightness-[0.97] focus-visible:outline-2 focus-visible:outline-[var(--ink)] md:gap-3 md:rounded-2xl md:px-3"
          >
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md border border-[var(--line)] bg-[var(--cream)] text-[var(--muted-2)] md:h-10 md:w-10 md:rounded-lg">
              <WalletCards className="h-4 w-4" />
            </span>
            <span className="min-w-0 flex-1">
              <span className="flex min-w-0 items-center gap-2">
                <span className="truncate text-sm font-semibold text-[var(--ink)]">{account.name}</span>
                {spend ? (
                  <span className="flex min-w-0 flex-1 items-center justify-center gap-2 overflow-hidden text-[10px] leading-none text-[var(--muted-2)]">
                    {SPEND_WINDOWS.map((days) => (
                      <span key={days} className="whitespace-nowrap">
                        <span className="font-semibold text-[var(--ink)]">
                          {formatAed((spend.get(account.id)?.[days] ?? 0) / 100)}
                        </span>{" "}
                        {t("spendDays", { days })}
                      </span>
                    ))}
                  </span>
                ) : (
                  <span className="flex-1" />
                )}
                <span className={`shrink-0 text-sm font-bold ${deltaClass}`}>{deltaLabel}</span>
              </span>
              {account.plusCents !== 0 || account.minusCents !== 0 ? (
                <span className="mt-0.5 flex min-w-0 flex-wrap items-center gap-1.5">
                  {account.plusCents !== 0 ? (
                    <span className="rounded-full bg-emerald-100 px-1.5 py-0.5 text-[10px] font-semibold text-emerald-800">
                      +{formatAed(account.plusCents / 100)}
                    </span>
                  ) : null}
                  {account.minusCents !== 0 ? (
                    <span className="rounded-full bg-rose-100 px-1.5 py-0.5 text-[10px] font-semibold text-rose-800">
                      {formatAed(account.minusCents / 100)}
                    </span>
                  ) : null}
                </span>
              ) : null}
            </span>
            <ChevronRight className="h-4 w-4 shrink-0 text-[var(--muted-2)]" />
          </Link>
        );
      })}
    </div>
  );
}
