"use client";

import { Suspense, type ReactNode } from "react";
import { useLocale, useTranslations } from "next-intl";
import { Calendar, ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { MondayDatePicker } from "@/components/crm/MondayDatePicker";
import { FinanceAuthGate } from "@/components/finance/FinanceAuthGate";
import { Link } from "@/i18n/navigation";
import {
  shiftFinanceDate,
  shiftFinanceMonth,
  useFinancePeriod,
  type FinancePeriod,
} from "@/hooks/useFinancePeriod";
import { useFinanceTransactions } from "@/hooks/useFinanceTransactions";
import type { FinanceTransaction } from "@/lib/api/types";
import { formatCrmMonth, getTbilisiTodayIsoDate } from "@/lib/format";

export type FinanceSection = "operations" | "income" | "expenses";

const SECTIONS: { section: FinanceSection; href: string; label: "operations" | "income" | "expenses" }[] = [
  { section: "operations", href: "/finance", label: "operations" },
  { section: "income", href: "/finance/income", label: "income" },
  { section: "expenses", href: "/finance/expenses", label: "expenses" },
];

export function FinanceBoard({
  section,
  children,
}: {
  section: FinanceSection;
  children: (transactions: FinanceTransaction[], period: FinancePeriod) => ReactNode;
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
  children: (transactions: FinanceTransaction[], period: FinancePeriod) => ReactNode;
}) {
  const t = useTranslations("finance");
  const locale = useLocale();
  const period = useFinancePeriod();
  const query = useFinanceTransactions(period);
  const today = getTbilisiTodayIsoDate();
  const isToday = period.date === today;
  const isCurrentMonth = period.month === today.slice(0, 7);

  return (
    <div className="grid gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <nav className="flex flex-wrap gap-2">
          {SECTIONS.map((item) => (
            <Button key={item.section} asChild variant={item.section === section ? "primary" : "outline"}>
              <Link href={`${item.href}?${period.query}`}>{t(item.label)}</Link>
            </Button>
          ))}
        </nav>
        <div className="flex gap-2">
          <Button
            type="button"
            variant={period.mode === "day" ? "primary" : "outline"}
            onClick={() => period.setMode("day")}
          >
            {t("day")}
          </Button>
          <Button
            type="button"
            variant={period.mode === "month" ? "primary" : "outline"}
            onClick={() => period.setMode("month")}
          >
            {t("month")}
          </Button>
        </div>
      </div>

      <div className="rounded-3xl border border-[var(--line)] bg-white p-6 shadow-sm">
        {period.mode === "day" ? (
          <div className="flex flex-col items-center justify-between gap-4 sm:flex-row">
            <Button
              variant="outline"
              size="sm"
              onClick={() => period.setDate(shiftFinanceDate(period.date, -1))}
              className="flex items-center gap-1.5"
            >
              <ChevronLeft className="h-4 w-4" />
              <span>{t("previousDay")}</span>
            </Button>
            <div className="flex w-full max-w-md flex-col items-center gap-1 text-center">
              <MondayDatePicker value={period.date} onChange={period.setDate} />
              <div className="flex items-center gap-2">
                {isToday ? (
                  <span className="rounded-full bg-[var(--brand)]/15 px-2.5 py-0.5 text-xs font-semibold text-[var(--brand)]">
                    {t("today")}
                  </span>
                ) : (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => period.setDate(today)}
                    className="h-7 text-xs font-medium text-[var(--brand)] hover:text-[var(--brand)]"
                  >
                    {t("jumpToToday")}
                  </Button>
                )}
              </div>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => period.setDate(shiftFinanceDate(period.date, 1))}
              className="flex items-center gap-1.5"
            >
              <span>{t("nextDay")}</span>
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        ) : (
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
        )}
      </div>

      {query.isError ? (
        <p className="text-sm text-[var(--danger)]">{t("loadError")}</p>
      ) : !query.data ? (
        <div className="flex min-h-[40vh] items-center justify-center">
          <Spinner className="h-6 w-6 text-[var(--brand)]" />
        </div>
      ) : (
        children(query.data.transactions, period)
      )}
    </div>
  );
}
