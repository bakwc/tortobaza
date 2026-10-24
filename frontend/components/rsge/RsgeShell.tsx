"use client";

import { Suspense, type ReactNode } from "react";
import { useLocale, useTranslations } from "next-intl";
import { Calendar, ChevronLeft, ChevronRight } from "lucide-react";
import { SectionShell, type SectionTab } from "@/components/menu/SectionShell";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { shiftFinanceMonth, useFinancePeriod, type FinancePeriod } from "@/hooks/useFinancePeriod";
import { formatCrmMonth, getTbilisiTodayIsoDate } from "@/lib/format";

export type RsgeSection = "waybills" | "invoices";

export function RsgeShell({ section, children }: { section: RsgeSection; children: ReactNode }) {
  return (
    <Suspense
      fallback={
        <div className="mx-auto flex min-h-[40vh] w-full max-w-5xl items-center justify-center px-4 py-8">
          <Spinner className="h-6 w-6 text-[var(--brand)]" />
        </div>
      }
    >
      <RsgeShellContent section={section}>{children}</RsgeShellContent>
    </Suspense>
  );
}

function RsgeShellContent({ section, children }: { section: RsgeSection; children: ReactNode }) {
  const t = useTranslations("rsge");
  const period = useFinancePeriod();
  const tabs: SectionTab[] = [
    { key: "waybills", href: `/rsge?${period.query}`, label: t("waybills") },
    { key: "invoices", href: `/rsge/invoices?${period.query}`, label: t("invoices") },
  ];
  return (
    <SectionShell active={section} financeOnly tabs={tabs}>
      <RsgeMonthBar period={period} />
      {children}
    </SectionShell>
  );
}

function RsgeMonthBar({ period }: { period: FinancePeriod }) {
  const t = useTranslations("rsge");
  const locale = useLocale();
  const today = getTbilisiTodayIsoDate();
  const isCurrentMonth = period.month === today.slice(0, 7);

  return (
    <div className="rounded-2xl border border-[var(--line)] bg-white p-4 shadow-sm">
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
  );
}
