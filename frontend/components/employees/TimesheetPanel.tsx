"use client";

import { useTranslations } from "next-intl";
import { QueryState } from "@/components/menu/ui";
import { EmployeesMonthBar, ScheduleGrid, dayTypeClass, shortDayType } from "@/components/employees/ScheduleGrid";
import { useFinancePeriod } from "@/hooks/useFinancePeriod";
import { useTimesheet } from "@/hooks/useSchedule";
import { cn } from "@/lib/utils";

export function TimesheetPanel() {
  const t = useTranslations("employees");
  const period = useFinancePeriod();
  const timesheet = useTimesheet(period.month);
  const grid = timesheet.data;

  return (
    <div className="grid gap-6">
      <EmployeesMonthBar />
      <QueryState isLoading={timesheet.isLoading} isError={timesheet.isError}>
        {grid ? (
          <div className="rounded-2xl border border-[var(--line)] bg-white p-4 shadow-sm md:rounded-3xl md:p-6">
            {grid.employees.length === 0 ? (
              <p className="text-sm text-[var(--muted-2)]">{t("scheduleEmpty")}</p>
            ) : (
              <ScheduleGrid
                start={grid.start}
                end={grid.end}
                employees={grid.employees}
                highlightUserId={null}
                rowExtraHeader={t("hours")}
                renderCell={(employee, date) => {
                  const cell = employee.days[date];
                  const hours = cell?.hours ?? "0.00";
                  const value = cell?.day_type ?? null;
                  const label = hours === "0.00" ? shortDayType(value, t) : String(Number(hours));
                  return (
                    <div
                      className={cn(
                        "flex h-8 min-w-8 items-center justify-center text-[10px] font-semibold tabular-nums leading-none",
                        dayTypeClass(value),
                        cell?.mismatch && "text-rose-700 ring-1 ring-inset ring-rose-600",
                      )}
                    >
                      {label}
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
