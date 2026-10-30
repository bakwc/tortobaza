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

function DayLabel({ date, locale }: { date: string; locale: string }) {
  return (
    <>
      <div>{Number(date.slice(8, 10))}</div>
      <div className="font-normal normal-case">{weekdayLabel(date, locale)}</div>
    </>
  );
}

function EmployeeName({ name }: { name: string }) {
  const words = name.trim().split(/\s+/);
  return (
    <div className="text-xs font-semibold normal-case leading-tight tracking-normal text-[var(--ink)]">
      {words.length === 2 ? (
        <>
          <div>{words[0]}</div>
          <div>{words[1]}</div>
        </>
      ) : (
        name
      )}
    </div>
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
  const today = getTbilisiTodayIsoDate();

  return (
    <div className="overflow-x-auto">
      <table className="w-max table-fixed border-separate border-spacing-0 text-sm">
        <colgroup>
          <col className="w-12" />
          {employees.map((employee) => (
            <col key={employee.id} className="w-20" />
          ))}
        </colgroup>
        <thead>
          <tr className="text-left text-[10px] uppercase tracking-wide text-[var(--ink)]/50">
            <th className="sticky left-0 z-20 w-12 min-w-12 max-w-12 bg-white px-1 py-2">{t("date")}</th>
            {employees.map((employee) => {
              const highlighted = employee.id === highlightUserId;
              return (
                <th
                  key={employee.id}
                  className={cn(
                    "w-20 min-w-20 max-w-20 px-1 py-2 text-center font-medium normal-case",
                    highlighted ? "bg-[var(--brand)]/10" : "bg-white",
                  )}
                >
                  <EmployeeName name={employee.name} />
                  <div className="truncate text-[10px] font-normal tracking-normal text-[var(--ink)]/50">
                    {employee.position}
                  </div>
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {dates.map((date) => {
            const isToday = date === today;
            return (
              <tr key={date}>
                <td
                  className={cn(
                    "sticky left-0 z-10 w-12 min-w-12 max-w-12 px-1 py-1 text-center text-[10px] font-medium",
                    isToday
                      ? "bg-[var(--brand)] text-xs font-bold text-white"
                      : isWeekend(date)
                        ? "bg-neutral-100 text-[var(--ink)]/70"
                        : "bg-white text-[var(--ink)]/50",
                  )}
                >
                  <DayLabel date={date} locale={locale} />
                </td>
                {employees.map((employee) => {
                  const highlighted = employee.id === highlightUserId;
                  return (
                    <td
                      key={employee.id}
                      className={cn(
                        "border border-white p-0 text-center",
                        highlighted ? "bg-[var(--brand)]/10" : isWeekend(date) && "bg-neutral-50",
                        isToday &&
                          "relative after:pointer-events-none after:absolute after:inset-0 after:z-10 after:shadow-[inset_0_0_0_2px_var(--brand)] after:content-['']",
                      )}
                    >
                      {renderCell(employee, date)}
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
        {renderRowExtra !== null ? (
          <tfoot>
            <tr>
              <td className="sticky left-0 z-10 w-12 min-w-12 max-w-12 whitespace-normal bg-white px-1 py-2 text-[10px] font-medium uppercase tracking-wide text-[var(--ink)]/50">
                {rowExtraHeader}
              </td>
              {employees.map((employee) => {
                const highlighted = employee.id === highlightUserId;
                return (
                  <td
                    key={employee.id}
                    className={cn(
                      "whitespace-normal px-1 py-1 align-top",
                      highlighted && "bg-[var(--brand)]/10",
                    )}
                  >
                    {renderRowExtra(employee)}
                  </td>
                );
              })}
            </tr>
          </tfoot>
        ) : null}
      </table>
    </div>
  );
}
