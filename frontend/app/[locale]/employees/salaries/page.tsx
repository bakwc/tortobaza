"use client";

import { Suspense } from "react";
import { useLocale, useTranslations } from "next-intl";
import { Calendar, ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { EmployeesShell } from "@/components/employees/EmployeesShell";
import { shiftFinanceMonth, useFinancePeriod } from "@/hooks/useFinancePeriod";
import { useCrmSalaries } from "@/hooks/useCrmOrders";
import type { CrmSalaryPeriod } from "@/lib/api/types";
import { formatAed, formatCrmMonth, getTbilisiTodayIsoDate } from "@/lib/format";

function dayNumber(isoDate: string): number {
  return Number(isoDate.slice(8, 10));
}

export default function EmployeesSalariesPage() {
  return (
    <EmployeesShell section="salaries">
      <Suspense>
        <SalariesBoard />
      </Suspense>
    </EmployeesShell>
  );
}

function SalariesBoard() {
  const t = useTranslations("crm");
  const locale = useLocale();
  const period = useFinancePeriod();
  const salariesQuery = useCrmSalaries(period.month);
  const today = getTbilisiTodayIsoDate();
  const isCurrentMonth = period.month === today.slice(0, 7);

  return (
    <div className="grid gap-6">
      <div className="rounded-2xl border border-[var(--line)] bg-white p-4 shadow-sm md:rounded-3xl md:p-6">
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

      {salariesQuery.isError ? (
        <p className="text-sm text-[var(--danger)]">{t("salaryLoadError")}</p>
      ) : !salariesQuery.data ? (
        <div className="flex min-h-[40vh] items-center justify-center">
          <Spinner className="h-6 w-6 text-[var(--brand)]" />
        </div>
      ) : (
        <>
          {salariesQuery.data.periods.map((periodRow) => (
            <SalaryPeriodTable key={periodRow.start} period={periodRow} />
          ))}
          <div className="rounded-2xl border border-[var(--line)] bg-white p-4 shadow-sm md:rounded-3xl md:p-6">
            <h2 className="text-base font-semibold text-[var(--ink)]">{t("salaryMonthTotal")}</h2>
            <div className="mt-3 grid gap-2 text-sm font-semibold text-[var(--ink)]">
              <div className="flex flex-wrap items-baseline justify-between gap-3">
                <span>{t("salaryHourlyTotal")}</span>
                <div className="flex gap-6 tabular-nums">
                  <span>{salariesQuery.data.hourly_hours}</span>
                  <span>{formatAed(salariesQuery.data.hourly_money)}</span>
                </div>
              </div>
              <div className="flex flex-wrap items-baseline justify-between gap-3">
                <span>{t("salaryMonthlyTotal")}</span>
                <div className="flex gap-6 tabular-nums">
                  <span>{salariesQuery.data.monthly_hours}</span>
                  <span>{formatAed(salariesQuery.data.monthly_money)}</span>
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function SalaryPeriodTable({ period }: { period: CrmSalaryPeriod }) {
  const t = useTranslations("crm");
  const employeesT = useTranslations("employees");

  return (
    <section className="rounded-2xl border border-[var(--line)] bg-white p-4 shadow-sm md:rounded-3xl md:p-6">
      <h2 className="text-base font-semibold text-[var(--ink)]">
        {dayNumber(period.start)}–{dayNumber(period.end)}
      </h2>
      {period.employees.length === 0 ? (
        <p className="mt-4 text-sm text-[var(--muted-2)]">{t("salaryEmpty")}</p>
      ) : null}
      <div className="mt-4 overflow-x-auto">
        <table className="w-full min-w-[24rem] text-sm">
          {period.employees.length === 0 ? null : (
            <>
              <thead>
                <tr className="border-b border-[var(--line)] text-left text-xs font-medium uppercase tracking-wide text-[var(--ink)]/60">
                  <th className="pb-3 pr-4 font-medium">{t("salaryEmployee")}</th>
                  <th className="pb-3 pr-4 font-medium">{employeesT("position")}</th>
                  <th className="pb-3 pr-4 font-medium">{t("salaryHours")}</th>
                  <th className="pb-3 font-medium">{t("salaryEarned")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--line)]">
                {period.employees.map((employee) => (
                  <tr key={employee.id}>
                    <td className="py-3 pr-4 text-[var(--ink)]">{employee.name}</td>
                    <td className="py-3 pr-4 text-[var(--ink)]">{employee.position}</td>
                    <td className="py-3 pr-4 tabular-nums font-medium text-[var(--ink)]">{employee.hours}</td>
                    <td className="py-3 tabular-nums font-medium text-[var(--ink)]">{formatAed(employee.money)}</td>
                  </tr>
                ))}
              </tbody>
            </>
          )}
          <tfoot>
            <tr className="border-t border-[var(--line)]">
              <td className="pt-3 pr-4 font-semibold text-[var(--ink)]" colSpan={2}>
                {t("salaryHourlyTotal")}
              </td>
              <td className="pt-3 pr-4 tabular-nums font-semibold text-[var(--ink)]">{period.hourly_hours}</td>
              <td className="pt-3 tabular-nums font-semibold text-[var(--ink)]">{formatAed(period.hourly_money)}</td>
            </tr>
            <tr>
              <td className="pt-3 pr-4 font-semibold text-[var(--ink)]" colSpan={2}>
                {t("salaryMonthlyTotal")}
              </td>
              <td className="pt-3 pr-4 tabular-nums font-semibold text-[var(--ink)]">{period.monthly_hours}</td>
              <td className="pt-3 tabular-nums font-semibold text-[var(--ink)]">{formatAed(period.monthly_money)}</td>
            </tr>
          </tfoot>
        </table>
      </div>
    </section>
  );
}
