"use client";

import { useLocale, useTranslations } from "next-intl";
import { ChevronRight, WalletCards } from "lucide-react";
import { Link } from "@/i18n/navigation";
import type { FinanceTransaction } from "@/lib/api/types";
import { formatAed } from "@/lib/format";

type AccountSummary = {
  id: number;
  name: string;
  total: number;
  plus: number;
  plusCents: number;
  minus: number;
  minusCents: number;
  deltaCents: number;
};

function summarize(transactions: FinanceTransaction[]): AccountSummary[] {
  const byId = new Map<number, AccountSummary>();
  for (const tx of transactions) {
    const cents = Math.round(Number.parseFloat(tx.amount) * 100);
    const existing = byId.get(tx.account.id);
    const row = existing ?? {
      id: tx.account.id,
      name: tx.account.name,
      total: 0,
      plus: 0,
      plusCents: 0,
      minus: 0,
      minusCents: 0,
      deltaCents: 0,
    };
    row.total += 1;
    if (cents > 0) {
      row.plus += 1;
      row.plusCents += cents;
    }
    if (cents < 0) {
      row.minus += 1;
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
}: {
  transactions: FinanceTransaction[];
  periodQuery: string;
}) {
  const t = useTranslations("finance");
  const locale = useLocale();

  if (transactions.length === 0) {
    return (
      <div className="rounded-3xl border border-[var(--line)] bg-white p-8 text-center text-sm text-[var(--muted-2)] shadow-sm">
        {t("empty")}
      </div>
    );
  }

  const accounts = summarize(transactions).sort((a, b) => a.name.localeCompare(b.name, locale));

  return (
    <div className="grid gap-2">
      {accounts.map((account) => {
        const delta = account.deltaCents / 100;
        const deltaClass =
          delta > 0 ? "text-emerald-700" : delta < 0 ? "text-rose-700" : "text-[var(--ink)]";
        const deltaLabel = delta > 0 ? `+${formatAed(delta)}` : formatAed(delta);
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
              <span className="flex min-w-0 items-center justify-between gap-2">
                <span className="truncate text-sm font-semibold text-[var(--ink)]">{account.name}</span>
                <span className={`shrink-0 text-sm font-bold ${deltaClass}`}>{deltaLabel}</span>
              </span>
              <span className="mt-0.5 flex min-w-0 flex-wrap items-center gap-1.5">
                <span className="rounded-full bg-[var(--cream)] px-1.5 py-0.5 text-[10px] font-semibold text-[var(--muted-2)]">
                  {t("operationCount", { count: account.total })}
                </span>
                <span className="rounded-full bg-emerald-100 px-1.5 py-0.5 text-[10px] font-semibold text-emerald-800">
                  +{account.plus} (+{formatAed(account.plusCents / 100)})
                </span>
                <span className="rounded-full bg-rose-100 px-1.5 py-0.5 text-[10px] font-semibold text-rose-800">
                  −{account.minus} ({formatAed(account.minusCents / 100)})
                </span>
              </span>
            </span>
            <ChevronRight className="h-4 w-4 shrink-0 text-[var(--muted-2)]" />
          </Link>
        );
      })}
    </div>
  );
}
