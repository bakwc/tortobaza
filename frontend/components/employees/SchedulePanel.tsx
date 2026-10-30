"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { EditorDialog } from "@/components/menu/EditorDialog";
import { Field, NativeSelect, QueryState } from "@/components/menu/ui";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScheduleGrid, dayTypeClass } from "@/components/employees/ScheduleGrid";
import { useFillSchedule, useSaveSchedule, useSchedule } from "@/hooks/useSchedule";
import { useFinancePeriod } from "@/hooks/useFinancePeriod";
import type { ScheduleDayType } from "@/lib/api/types";
import { cn } from "@/lib/utils";

const PATTERNS: Record<PatternKey, ScheduleDayType[]> = {
  "4_2": ["work", "work", "work", "work", "off", "off"],
  "2_2": ["work", "work", "off", "off"],
  "5_2": ["work", "work", "work", "work", "work", "off", "off"],
  every: ["work"],
};

type PatternKey = "4_2" | "2_2" | "5_2" | "every";

function countsFor(days: Record<string, ScheduleDayType>) {
  const counts = { work: 0, off: 0, vacation: 0, sick: 0 };
  for (const dayType of Object.values(days)) {
    counts[dayType] += 1;
  }
  return counts;
}

function scheduledType(days: Record<string, ScheduleDayType>, date: string): ScheduleDayType | null {
  if (date in days) return days[date];
  return null;
}

export function SchedulePanel() {
  const t = useTranslations("employees");
  const period = useFinancePeriod();
  const schedule = useSchedule(period.month);
  const save = useSaveSchedule(period.month);
  const fill = useFillSchedule(period.month);
  const [patternFor, setPatternFor] = useState<number | null>(null);
  const [patternKey, setPatternKey] = useState<PatternKey>("4_2");
  const [cycleStart, setCycleStart] = useState("");

  const openPattern = (userId: number) => {
    fill.reset();
    setPatternKey("4_2");
    setCycleStart(`${period.month}-01`);
    setPatternFor(userId);
  };

  const grid = schedule.data;
  const patternEmployee = grid?.employees.find((employee) => employee.id === patternFor) ?? null;

  return (
    <div className="grid gap-6">
      {save.isError ? <p className="text-sm text-[var(--danger)]">{t("scheduleSaveError")}</p> : null}
      <QueryState isLoading={schedule.isLoading} isError={schedule.isError}>
        {grid ? (
          <div className="rounded-2xl border border-[var(--line)] bg-white p-4 shadow-sm md:rounded-3xl md:p-6">
            <h2 className="mb-4 text-lg font-semibold text-[var(--ink)]">{t("schedulePlanTitle")}</h2>
            {grid.employees.length === 0 ? (
              <p className="text-sm text-[var(--muted-2)]">{t("scheduleEmpty")}</p>
            ) : (
              <ScheduleGrid
                start={grid.start}
                end={grid.end}
                employees={grid.employees}
                highlightUserId={null}
                rowExtraHeader={t("pattern")}
                renderCell={(employee, date) => {
                  const value = scheduledType(employee.days, date);
                  return (
                    <select
                      aria-label={t("dayType")}
                      value={value ?? ""}
                      disabled={save.isPending}
                      onChange={(event) => {
                        const next = event.target.value;
                        save.mutate([
                          {
                            user: employee.id,
                            date,
                            day_type: next === "" ? null : (next as ScheduleDayType),
                          },
                        ]);
                      }}
                      className={cn(
                        "h-8 w-10 appearance-none border-0 text-center text-[10px] font-semibold",
                        dayTypeClass(value),
                      )}
                    >
                      <option value="">{t("dayEmpty")}</option>
                      <option value="work">{t("dayWorkShort")}</option>
                      <option value="off">{t("dayOffShort")}</option>
                      <option value="vacation">{t("dayVacationShort")}</option>
                      <option value="sick">{t("daySickShort")}</option>
                    </select>
                  );
                }}
                renderRowExtra={(employee) => {
                  const counts = countsFor(employee.days);
                  return (
                    <div className="flex flex-col items-start gap-1">
                      <Button
                        type="button"
                        size="sm"
                        variant="outline"
                        className="h-auto w-full whitespace-normal px-1 py-1 text-center text-xs"
                        onClick={() => openPattern(employee.id)}
                      >
                        {t("fillPattern")}
                      </Button>
                      <span className="whitespace-normal text-xs tabular-nums text-[var(--ink)]/70">
                        {t("dayWorkShort")} {counts.work} {t("dayOffShort")} {counts.off} {t("dayVacationShort")}{" "}
                        {counts.vacation} {t("daySickShort")} {counts.sick}
                      </span>
                    </div>
                  );
                }}
              />
            )}
          </div>
        ) : null}
      </QueryState>
      {patternFor !== null && grid && patternEmployee ? (
        <EditorDialog
          open
          onOpenChange={(value) => (value ? null : setPatternFor(null))}
          onCancel={null}
          title={patternEmployee.name}
          pending={fill.isPending}
          error={fill.error}
          submitLabel={t("fillPattern")}
          onSubmit={() =>
            fill.mutate(
              {
                user: patternFor,
                start: grid.start,
                end: grid.end,
                cycle_start: cycleStart,
                pattern: PATTERNS[patternKey],
              },
              { onSuccess: () => setPatternFor(null) },
            )
          }
          onDelete={null}
          deletePending={false}
          headerAction={null}
          below={null}
        >
          <Field label={t("pattern")}>
            <NativeSelect
              value={patternKey}
              onChange={(event) => setPatternKey(event.target.value as PatternKey)}
            >
              <option value="4_2">{t("pattern42")}</option>
              <option value="2_2">{t("pattern22")}</option>
              <option value="5_2">{t("pattern52")}</option>
              <option value="every">{t("patternEvery")}</option>
            </NativeSelect>
          </Field>
          <Field label={t("cycleStart")}>
            <Input required type="date" value={cycleStart} onChange={(event) => setCycleStart(event.target.value)} />
          </Field>
        </EditorDialog>
      ) : null}
    </div>
  );
}
