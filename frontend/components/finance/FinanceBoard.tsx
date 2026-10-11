"use client";

import { Suspense, type ReactNode } from "react";
import { useSearchParams } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { Calendar, ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { FinanceAuthGate } from "@/components/finance/FinanceAuthGate";
import { Link } from "@/i18n/navigation";
import { useExchangeRates } from "@/hooks/useExchangeRates";
import {
  shiftFinanceMonth,
  useFinancePeriod,
  type FinancePeriod,
} from "@/hooks/useFinancePeriod";
import { useFinanceTransactions } from "@/hooks/useFinanceTransactions";
import type { FinanceTransaction } from "@/lib/api/types";
import { formatCrmMonth, getTbilisiTodayIsoDate } from "@/lib/format";

export type FinanceSection = "operations" | "income" | "expenses" | "accounts";

const SECTIONS: { section: FinanceSection; href: string; label: FinanceSection }[] = [
  { section: "operations", href: "/finance", label: "operations" },
  { section: "income", href: "/finance/income", label: "income" },
  { section: "expenses", href: "/finance/expenses", label: "expenses" },
  { section: "accounts", href: "/finance/accounts", label: "accounts" },
];

export function FinanceBoard({
  section,
  children,
}: {
  section: FinanceSection;
  children: (
    transactions: FinanceTransaction[],
    period: FinancePeriod,
    rates: Record<string, string>,
  ) => ReactNode;
}) {
  return (
    <div className="mx-auto w-full max-w-5xl px-4 py-8 md:py-12">
      <FinanceAuthGate>
        <Suspense
          fallback={
            <div className="flex min-h-[40vh] items-center justify-center">
              <Spinner className="h-6 w-6 text-[var(--brand)]" />
            </div>
          }
        >
          <FinanceBoardContent section={section}>{children}</FinanceBoardContent>
        </Suspense>
      </FinanceAuthGate>
    </div>
  );
}

function FinanceBoardContent({
  section,
  children,
}: {
  section: FinanceSection;
  children: (
    transactions: FinanceTransaction[],
    period: FinancePeriod,
    rates: Record<string, string>,
  ) => ReactNode;
}) {
  const t = useTranslations("finance");
  const locale = useLocale();
  const searchParams = useSearchParams();
  const period = useFinancePeriod();
  const currentQuery = searchParams.toString();
  const query = useFinanceTransactions(period);
  const ratesQuery = useExchangeRates();
  const today = getTbilisiTodayIsoDate();
  const isCurrentMonth = period.month === today.slice(0, 7);

  return (
    <div className="grid gap-6">
      <nav className="flex flex-wrap gap-2">
        {SECTIONS.map((item) => (
          <Button key={item.section} asChild variant={item.section === section ? "primary" : "outline"}>
            <Link
              href={`${item.href}?${item.section === section && currentQuery ? currentQuery : period.query}`}
            >
              {t(item.label)}
            </Link>
          </Button>
        ))}
      </nav>

      <div className="rounded-3xl border border-[var(--line)] bg-white p-6 shadow-sm">
        <div className="flex items-center justify-between gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => period.setMonth(shiftFinanceMonth(period.month, -1))}
            className="h-9 w-9 shrink-0 px-0 sm:w-auto sm:px-4"
          >
            <ChevronLeft className="h-4 w-4" />
            <span className="hidden sm:inline">{t("prevMonth")}</span>
          </Button>
          <div className="flex min-w-0 flex-1 flex-col items-center gap-1 text-center">
            <div className="flex items-center gap-2 text-base font-semibold text-[var(--ink)] md:text-lg">
              <Calendar className="h-4 w-4 shrink-0 text-[var(--brand)] md:h-5 md:w-5" />
              <span className="truncate">{formatCrmMonth(period.month, locale)}</span>
            </div>
            <div className="flex items-center gap-2">
              {isCurrentMonth ? (
                <span className="rounded-full bg-[var(--brand)]/15 px-2.5 py-0.5 text-xs font-semibold text-[var(--brand)]">
                  {t("thisMonth")}
                </span>
              ) : (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => period.setMonth(today.slice(0, 7))}
                  className="h-7 text-xs font-medium text-[var(--brand)] hover:text-[var(--brand)]"
                >
                  {t("jumpToThisMonth")}
                </Button>
              )}
            </div>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => period.setMonth(shiftFinanceMonth(period.month, 1))}
            className="h-9 w-9 shrink-0 px-0 sm:w-auto sm:px-4"
          >
            <span className="hidden sm:inline">{t("nextMonth")}</span>
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {query.isError || ratesQuery.isError ? (
        <p className="text-sm text-[var(--danger)]">{t("loadError")}</p>
      ) : !query.data || !ratesQuery.data ? (
        <div className="flex min-h-[40vh] items-center justify-center">
          <Spinner className="h-6 w-6 text-[var(--brand)]" />
        </div>
      ) : (
        children(query.data.transactions, period, ratesQuery.data.rates)
      )}
    </div>
  );
}
