"use client";

import { Suspense, type ReactNode } from "react";
import { useSearchParams } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { Calendar, ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { CrmAuthGate } from "@/components/crm/CrmAuthGate";
import { CrmOverflowMenu } from "@/components/crm/CrmOverflowMenu";
import { useCurrentUser } from "@/hooks/useAuth";
import { shiftFinanceMonth, useFinancePeriod } from "@/hooks/useFinancePeriod";
import { Link } from "@/i18n/navigation";
import { formatCrmMonth, getTbilisiTodayIsoDate } from "@/lib/format";

export type AnalyticsSection = "overview" | "load" | "clients" | "products";

const SECTIONS: { section: AnalyticsSection; href: string }[] = [
  { section: "overview", href: "/analytics" },
  { section: "load", href: "/analytics/load" },
  { section: "clients", href: "/analytics/clients" },
  { section: "products", href: "/analytics/products" },
];

export function AnalyticsShell({ section, children }: { section: AnalyticsSection; children: ReactNode }) {
  return (
    <div className="mx-auto w-full max-w-5xl px-4 py-8 md:py-12">
      <CrmAuthGate>
        <Suspense
          fallback={
            <div className="flex min-h-[40vh] items-center justify-center">
              <Spinner className="h-6 w-6 text-[var(--brand)]" />
            </div>
          }
        >
          <AnalyticsShellContent section={section}>{children}</AnalyticsShellContent>
        </Suspense>
      </CrmAuthGate>
    </div>
  );
}

function AnalyticsShellContent({ section, children }: { section: AnalyticsSection; children: ReactNode }) {
  const t = useTranslations("analytics");
  const crm = useTranslations("crm");
  const locale = useLocale();
  const currentUser = useCurrentUser();
  const searchParams = useSearchParams();
  const period = useFinancePeriod();
  const currentQuery = searchParams.toString();
  const today = getTbilisiTodayIsoDate();
  const isCurrentMonth = period.month === today.slice(0, 7);
  const allowed = Boolean(currentUser.data?.is_finance_admin);
  const showPeriod = section === "load" || section === "products";

  if (!allowed) {
    return (
      <div className="grid gap-6">
        <div className="flex justify-end">
          <CrmOverflowMenu />
        </div>
        <div className="mx-auto max-w-md px-4 py-16 text-center text-sm text-[var(--ink)]">{crm("staffOnly")}</div>
      </div>
    );
  }

  return (
    <div className="grid min-w-0 grid-cols-[minmax(0,1fr)] gap-6">
      <div className="flex min-w-0 items-start justify-between gap-2">
        <nav className="flex min-w-0 flex-1 flex-wrap gap-2">
          {SECTIONS.map((item) => (
            <Button key={item.section} asChild variant={item.section === section ? "primary" : "outline"}>
              <Link
                href={`${item.href}?${item.section === section && currentQuery ? currentQuery : period.query}`}
              >
                {t(item.section)}
              </Link>
            </Button>
          ))}
        </nav>
        <div className="shrink-0">
          <CrmOverflowMenu />
        </div>
      </div>
      {showPeriod ? (
        <div className="min-w-0 rounded-3xl border border-[var(--line)] bg-white p-6 shadow-sm">
          <div className="flex items-center justify-between gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => period.setMonth(shiftFinanceMonth(period.month, -1))}
              className="h-9 w-9 shrink-0 px-0 sm:w-auto sm:px-4"
            >
              <ChevronLeft className="h-4 w-4" />
              <span className="hidden sm:inline">{crm("prevMonth")}</span>
            </Button>
            <div className="flex min-w-0 flex-1 flex-col items-center gap-1 text-center">
              <div className="flex items-center gap-2 text-base font-semibold text-[var(--ink)] md:text-lg">
                <Calendar className="h-4 w-4 shrink-0 text-[var(--brand)] md:h-5 md:w-5" />
                <span className="truncate">{formatCrmMonth(period.month, locale)}</span>
              </div>
              <div className="flex items-center gap-2">
                {isCurrentMonth ? (
                  <span className="rounded-full bg-[var(--brand)]/15 px-2.5 py-0.5 text-xs font-semibold text-[var(--brand)]">
                    {crm("thisMonth")}
                  </span>
                ) : (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => period.setMonth(today.slice(0, 7))}
                    className="h-7 text-xs font-medium text-[var(--brand)] hover:text-[var(--brand)]"
                  >
                    {crm("jumpToThisMonth")}
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
              <span className="hidden sm:inline">{crm("nextMonth")}</span>
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      ) : null}
      {children}
    </div>
  );
}
