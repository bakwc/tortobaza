"use client";

import { useLocale, useTranslations } from "next-intl";
import type { FinanceTransaction } from "@/lib/api/types";
import { formatAed } from "@/lib/format";

type AccountSummary = {
  id: number;
  name: string;
  total: number;
  plus: number;
  minus: number;
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
      minus: 0,
      deltaCents: 0,
    };
    row.total += 1;
    if (cents > 0) row.plus += 1;
    if (cents < 0) row.minus += 1;
    row.deltaCents += cents;
    if (!existing) byId.set(tx.account.id, row);
  }
  return [...byId.values()];
}

export function FinanceAccountList({ transactions }: { transactions: FinanceTransaction[] }) {
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
    <div className="grid gap-3">
      {accounts.map((account) => {
        const delta = account.deltaCents / 100;
        const deltaClass =
          delta > 0 ? "text-emerald-700" : delta < 0 ? "text-rose-700" : "text-[var(--ink)]";
        const deltaLabel = delta > 0 ? `+${formatAed(delta)}` : formatAed(delta);
        return (
          <section
            key={account.id}
            className="rounded-3xl border border-[var(--line)] bg-white p-6 shadow-sm"
          >
            <h2 className="text-base font-semibold text-[var(--ink)]">{account.name}</h2>
            <dl className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-4">
              <div>
                <dt className="text-xs font-semibold uppercase tracking-wide text-[var(--ink)]/60">
                  {t("operations")}
                </dt>
                <dd className="mt-1 text-lg font-semibold text-[var(--ink)]">{account.total}</dd>
              </div>
              <div>
                <dt className="text-xs font-semibold uppercase tracking-wide text-[var(--ink)]/60">
                  {t("plus")}
                </dt>
                <dd className="mt-1 text-lg font-semibold text-emerald-700">{account.plus}</dd>
              </div>
              <div>
                <dt className="text-xs font-semibold uppercase tracking-wide text-[var(--ink)]/60">
                  {t("minus")}
                </dt>
                <dd className="mt-1 text-lg font-semibold text-rose-700">{account.minus}</dd>
              </div>
              <div>
                <dt className="text-xs font-semibold uppercase tracking-wide text-[var(--ink)]/60">
                  {t("balanceChange")}
                </dt>
                <dd className={`mt-1 text-lg font-semibold ${deltaClass}`}>{deltaLabel}</dd>
              </div>
            </dl>
          </section>
        );
      })}
    </div>
  );
}
