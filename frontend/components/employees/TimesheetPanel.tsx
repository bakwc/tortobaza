"use client";

import { useTranslations } from "next-intl";
import { QueryState } from "@/components/menu/ui";
import { ScheduleGrid, dayTypeClass, shortDayType } from "@/components/employees/ScheduleGrid";
import { useFinancePeriod } from "@/hooks/useFinancePeriod";
import { useTimesheet } from "@/hooks/useSchedule";
import { cn } from "@/lib/utils";

const TIMESHEET_COLUMN = "w-28 min-w-28 max-w-28";

function clockSpan(arrival: string | null, departure: string | null): string | null {
  if (arrival !== null && departure !== null) return `${arrival} - ${departure}`;
  if (arrival !== null) return `${arrival} -`;
  if (departure !== null) return `- ${departure}`;
  return null;
}

export function TimesheetPanel() {
  const t = useTranslations("employees");
  const period = useFinancePeriod();
  const timesheet = useTimesheet(period.month);
  const grid = timesheet.data;

  return (
    <div className="grid gap-6">
      <QueryState isLoading={timesheet.isLoading} isError={timesheet.isError}>
        {grid ? (
          <div className="rounded-2xl border border-[var(--line)] bg-white p-4 shadow-sm md:rounded-3xl md:p-6">
            <h2 className="mb-4 text-lg font-semibold text-[var(--ink)]">{t("timesheetFactTitle")}</h2>
            {grid.employees.length === 0 ? (
              <p className="text-sm text-[var(--muted-2)]">{t("scheduleEmpty")}</p>
            ) : (
              <ScheduleGrid
                start={grid.start}
                end={grid.end}
                employees={grid.employees}
                highlightUserId={null}
                columnClassName={TIMESHEET_COLUMN}
                rowExtraHeader={t("hours")}
                renderCell={(employee, date) => {
                  const cell = employee.days[date];
                  const hours = cell?.hours ?? "0.00";
                  const value = cell?.day_type ?? null;
                  const label = hours === "0.00" ? shortDayType(value, t) : String(Number(hours));
                  const span = clockSpan(cell?.arrival ?? null, cell?.departure ?? null);
                  return (
                    <div
                      className={cn(
                        "flex min-h-8 w-full flex-col items-center justify-center gap-0.5 px-0.5 py-1 text-[10px] font-semibold tabular-nums leading-none",
                        dayTypeClass(value),
                        cell?.mismatch && "text-rose-700 ring-1 ring-inset ring-rose-600",
                      )}
                    >
                      <span>{label}</span>
                      {span !== null ? <span className="font-medium">{span}</span> : null}
                    </div>
                  );
                }}
                renderRowExtra={(employee) => (
                  <span className="tabular-nums font-medium">{employee.total_hours}</span>
                )}
              />
            )}
          </div>
        ) : null}
      </QueryState>
    </div>
  );
}
