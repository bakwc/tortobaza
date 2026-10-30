"use client";

import type { ReactNode } from "react";
import { useLocale, useTranslations } from "next-intl";
import { Calendar, ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { shiftFinanceMonth, useFinancePeriod } from "@/hooks/useFinancePeriod";
import type { ScheduleDayType } from "@/lib/api/types";
import { formatCrmMonth, getTbilisiTodayIsoDate } from "@/lib/format";
import { cn } from "@/lib/utils";

export type ScheduleGridEmployee = {
  id: number;
  name: string;
  position: string;
};

export function dayTypeClass(value: ScheduleDayType | null): string {
  if (value === "work") return "bg-emerald-100 text-emerald-950";
  if (value === "off") return "bg-neutral-200 text-neutral-800";
  if (value === "vacation") return "bg-amber-100 text-amber-950";
  if (value === "sick") return "bg-rose-100 text-rose-950";
  return "bg-transparent";
}

export function ScheduleDayCell({ value }: { value: ScheduleDayType | null }) {
  const t = useTranslations("employees");
  return (
    <div
      className={cn(
        "flex h-8 min-w-8 items-center justify-center text-[10px] font-semibold leading-none",
        dayTypeClass(value),
      )}
    >
      {shortDayType(value, t)}
    </div>
  );
}

export function shortDayType(
  value: ScheduleDayType | null,
  t: (key: "dayWorkShort" | "dayOffShort" | "dayVacationShort" | "daySickShort") => string,
): string {
  if (value === "work") return t("dayWorkShort");
  if (value === "off") return t("dayOffShort");
  if (value === "vacation") return t("dayVacationShort");
  if (value === "sick") return t("daySickShort");
  return "";
}

export function EmployeesMonthBar() {
  const t = useTranslations("crm");
  const locale = useLocale();
  const period = useFinancePeriod();
  const today = getTbilisiTodayIsoDate();
  const isCurrentMonth = period.month === today.slice(0, 7);

  return (
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
  );
}

function monthDates(start: string, end: string): string[] {
  const dates: string[] = [];
  let cursor = start;
  while (cursor <= end) {
    dates.push(cursor);
    cursor = shiftIsoDate(cursor);
  }
  return dates;
}

function shiftIsoDate(iso: string): string {
  const [year, month, day] = iso.split("-").map(Number);
  const next = new Date(Date.UTC(year, month - 1, day + 1));
  const nextYear = next.getUTCFullYear();
  const nextMonth = String(next.getUTCMonth() + 1).padStart(2, "0");
  const nextDay = String(next.getUTCDate()).padStart(2, "0");
  return `${nextYear}-${nextMonth}-${nextDay}`;
}

function isWeekend(iso: string): boolean {
  const [year, month, day] = iso.split("-").map(Number);
  const weekday = new Date(Date.UTC(year, month - 1, day)).getUTCDay();
  return weekday === 0 || weekday === 6;
}

function weekdayLabel(iso: string, locale: string): string {
  const [year, month, day] = iso.split("-").map(Number);
  return new Intl.DateTimeFormat(locale, { weekday: "short", timeZone: "UTC" }).format(
    new Date(Date.UTC(year, month - 1, day)),
  );
}

export function ScheduleGrid<T extends ScheduleGridEmployee>({
  start,
  end,
  employees,
  highlightUserId,
  renderCell,
  renderRowExtra,
  rowExtraHeader,
}: {
  start: string;
  end: string;
  employees: T[];
  highlightUserId: number | null;
  renderCell: (employee: T, date: string) => ReactNode;
  renderRowExtra: ((employee: T) => ReactNode) | null;
  rowExtraHeader: string | null;
}) {
  const t = useTranslations("employees");
  const locale = useLocale();
  const dates = monthDates(start, end);

  return (
    <div className="overflow-x-auto">
      <table className="border-separate border-spacing-0 text-sm">
        <thead>
          <tr className="text-left text-[10px] uppercase tracking-wide text-[var(--ink)]/50">
            <th className="sticky left-0 z-20 w-28 min-w-28 max-w-28 bg-white px-2 py-2">{t("name")}</th>
            <th className="sticky left-28 z-20 w-32 min-w-32 max-w-32 bg-white px-2 py-2">{t("position")}</th>
            {dates.map((date) => (
              <th
                key={date}
                className={cn(
                  "px-0 py-1 text-center font-medium",
                  isWeekend(date) && "bg-neutral-100 text-[var(--ink)]/70",
                )}
              >
                <div>{Number(date.slice(8, 10))}</div>
                <div className="font-normal normal-case">{weekdayLabel(date, locale)}</div>
              </th>
            ))}
            {rowExtraHeader !== null ? <th className="px-2 py-2">{rowExtraHeader}</th> : null}
          </tr>
        </thead>
        <tbody>
          {employees.map((employee) => {
            const highlighted = employee.id === highlightUserId;
            return (
              <tr key={employee.id} className={highlighted ? "bg-[var(--brand)]/10" : undefined}>
                <td
                  className={cn(
                    "sticky left-0 z-10 w-28 min-w-28 max-w-28 truncate px-2 py-1 font-medium text-[var(--ink)]",
                    highlighted ? "bg-[var(--brand)]/10" : "bg-white",
                  )}
                >
                  {employee.name}
                </td>
                <td
                  className={cn(
                    "sticky left-28 z-10 w-32 min-w-32 max-w-32 truncate px-2 py-1 text-[var(--ink)]/70",
                    highlighted ? "bg-[var(--brand)]/10" : "bg-white",
                  )}
                >
                  {employee.position}
                </td>
                {dates.map((date) => (
                  <td
                    key={date}
                    className={cn(
                      "border border-white p-0 text-center",
                      isWeekend(date) && "bg-neutral-50",
                    )}
                  >
                    {renderCell(employee, date)}
                  </td>
                ))}
                {renderRowExtra !== null ? (
                  <td className="whitespace-nowrap px-2 py-1">{renderRowExtra(employee)}</td>
                ) : null}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
