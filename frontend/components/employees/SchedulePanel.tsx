"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { EditorDialog } from "@/components/menu/EditorDialog";
import { Field, NativeSelect, QueryState } from "@/components/menu/ui";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScheduleGrid, dayTypeClass, shortDayType } from "@/components/employees/ScheduleGrid";
import { useFillSchedule, useSaveSchedule, useSchedule } from "@/hooks/useSchedule";
import { useFinancePeriod } from "@/hooks/useFinancePeriod";
import type { ScheduleDayType } from "@/lib/api/types";
import { cn } from "@/lib/utils";

const PATTERNS: Record<PatternKey, ScheduleDayType[]> = {
  "4_2": ["work", "work", "work", "work", "off", "off"],
  "4_3": ["work", "work", "work", "work", "off", "off", "off"],
  "2_2": ["work", "work", "off", "off"],
  "5_2": ["work", "work", "work", "work", "work", "off", "off"],
  every: ["work"],
};

type PatternKey = "4_2" | "4_3" | "2_2" | "5_2" | "every";

const APPLY_TYPES: (ScheduleDayType | null)[] = ["work", "off", "vacation", "sick", null];

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
  const [selected, setSelected] = useState<string[]>([]);
  const [selectedMonth, setSelectedMonth] = useState(period.month);
  if (selectedMonth !== period.month) {
    setSelectedMonth(period.month);
    setSelected([]);
  }

  const openPattern = (userId: number) => {
    fill.reset();
    setPatternKey("4_2");
    setCycleStart(`${period.month}-01`);
    setPatternFor(userId);
  };

  const grid = schedule.data;
  const patternEmployee = grid?.employees.find((employee) => employee.id === patternFor) ?? null;

  const toggleCell = (userId: number, date: string) => {
    const key = `${userId}:${date}`;
    setSelected((current) => (current.includes(key) ? current.filter((item) => item !== key) : [...current, key]));
  };

  const applyType = (dayType: ScheduleDayType | null) => {
    save.mutate(
      selected.map((key) => {
        const splitAt = key.indexOf(":");
        return {
          user: Number(key.slice(0, splitAt)),
          date: key.slice(splitAt + 1),
          day_type: dayType,
        };
      }),
      { onSuccess: () => setSelected([]) },
    );
  };

  return (
    <div className="grid gap-6">
      {save.isError ? <p className="text-sm text-[var(--danger)]">{t("scheduleSaveError")}</p> : null}
      <QueryState isLoading={schedule.isLoading} isError={schedule.isError}>
        {grid ? (
          <div className="rounded-2xl border border-[var(--line)] bg-white p-4 shadow-sm md:rounded-3xl md:p-6">
            <h2 className="mb-4 text-lg font-semibold text-[var(--ink)]">{t("schedulePlanTitle")}</h2>
            {selected.length > 0 ? (
              <div className="sticky top-0 z-30 mb-3 flex flex-wrap items-center gap-2 bg-white py-2">
                <span className="text-sm font-medium text-[var(--ink)]">{t("selectedDays", { count: selected.length })}</span>
                {APPLY_TYPES.map((dayType) => (
                  <Button
                    key={dayType ?? "empty"}
                    type="button"
                    size="sm"
                    variant="outline"
                    disabled={save.isPending}
                    className={cn("h-8 px-2", dayTypeClass(dayType))}
                    onClick={() => applyType(dayType)}
                  >
                    {dayType === null ? t("dayEmpty") : shortDayType(dayType, t)}
                  </Button>
                ))}
                <Button
                  type="button"
                  size="sm"
                  variant="ghost"
                  disabled={save.isPending}
                  onClick={() => setSelected([])}
                >
                  {t("clearSelection")}
                </Button>
              </div>
            ) : null}
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
                  const key = `${employee.id}:${date}`;
                  const isSelected = selected.includes(key);
                  return (
                    <button
                      type="button"
                      aria-label={t("dayType")}
                      aria-pressed={isSelected}
                      disabled={save.isPending}
                      onClick={() => toggleCell(employee.id, date)}
                      className={cn(
                        "flex h-8 w-full items-center justify-center text-[10px] font-semibold",
                        dayTypeClass(value),
                        isSelected && "ring-2 ring-inset ring-[var(--brand)]",
                      )}
                    >
                      {shortDayType(value, t)}
                    </button>
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
              <option value="4_3">{t("pattern43")}</option>
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
