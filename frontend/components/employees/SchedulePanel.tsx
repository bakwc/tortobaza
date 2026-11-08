"use client";

import { useEffect, useRef, useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { EditorDialog } from "@/components/menu/EditorDialog";
import { Field, NativeSelect, QueryState } from "@/components/menu/ui";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScheduleGrid, ScheduleSheet, dayTypeClass, shortDayType } from "@/components/employees/ScheduleGrid";
import { useCan } from "@/hooks/useAuth";
import { useFillSchedule, useSaveSchedule, useSchedule } from "@/hooks/useSchedule";
import { useFinancePeriod } from "@/hooks/useFinancePeriod";
import type { ScheduleDayType } from "@/lib/api/types";
import { formatCrmMonth } from "@/lib/format";
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

const PDF_MARGIN = 8;
const PDF_PAGE_WIDTH = 297 - PDF_MARGIN * 2;
const PDF_PAGE_HEIGHT = 210 - PDF_MARGIN * 2;

async function downloadSchedulePdf(node: HTMLElement, month: string) {
  const [{ toCanvas }, { jsPDF }] = await Promise.all([import("html-to-image"), import("jspdf")]);
  const canvas = await toCanvas(node, { pixelRatio: 2, backgroundColor: "#ffffff" });
  if (canvas.width === 0) throw new Error("canvas");
  const pdf = new jsPDF({ orientation: "landscape", unit: "mm", format: "a4" });
  const imgHeight = (canvas.height * PDF_PAGE_WIDTH) / canvas.width;
  const scale = canvas.width / PDF_PAGE_WIDTH;
  let offset = 0;
  let page = 0;
  while (offset < imgHeight - 0.01) {
    if (page > 0) pdf.addPage();
    const sliceMm = Math.min(PDF_PAGE_HEIGHT, imgHeight - offset);
    const sourceY = Math.round(offset * scale);
    const slicePx = Math.min(canvas.height - sourceY, Math.max(1, Math.round(sliceMm * scale)));
    const sliceCanvas = document.createElement("canvas");
    sliceCanvas.width = canvas.width;
    sliceCanvas.height = slicePx;
    const ctx = sliceCanvas.getContext("2d");
    if (ctx === null) throw new Error("canvas");
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, sliceCanvas.width, sliceCanvas.height);
    ctx.drawImage(canvas, 0, sourceY, canvas.width, slicePx, 0, 0, canvas.width, slicePx);
    pdf.addImage(sliceCanvas.toDataURL("image/png"), "PNG", PDF_MARGIN, PDF_MARGIN, PDF_PAGE_WIDTH, sliceMm);
    offset += sliceMm;
    page += 1;
  }
  pdf.save(`schedule-${month}.pdf`);
}

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
  const locale = useLocale();
  const canEdit = useCan("edit_schedule");
  const period = useFinancePeriod();
  const schedule = useSchedule(period.month);
  const save = useSaveSchedule(period.month);
  const fill = useFillSchedule(period.month);
  const sheetRef = useRef<HTMLDivElement>(null);
  const exportLock = useRef(false);
  const [exporting, setExporting] = useState(false);
  const [patternFor, setPatternFor] = useState<number | null>(null);
  const [patternKey, setPatternKey] = useState<PatternKey>("4_2");
  const [cycleStart, setCycleStart] = useState("");
  const [selected, setSelected] = useState<string[]>([]);
  const [selectedMonth, setSelectedMonth] = useState(period.month);
  if (selectedMonth !== period.month) {
    setSelectedMonth(period.month);
    setSelected([]);
  }

  useEffect(() => {
    if (!exporting || exportLock.current) return;
    const node = sheetRef.current;
    if (node === null) return;
    exportLock.current = true;
    void downloadSchedulePdf(node, period.month).then(() => {
      exportLock.current = false;
      setExporting(false);
    });
  }, [exporting, period.month]);

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
      {save.isError ? <p className="text-sm text-[var(--danger)] print:hidden">{t("scheduleSaveError")}</p> : null}
      <QueryState isLoading={schedule.isLoading} isError={schedule.isError}>
        {grid ? (
          <>
          <div className="rounded-2xl border border-[var(--line)] bg-white p-4 shadow-sm print:hidden md:rounded-3xl md:p-6">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <h2 className="text-lg font-semibold text-[var(--ink)]">{t("schedulePlanTitle")}</h2>
              {grid.employees.length > 0 ? (
                <div className="flex gap-2">
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    disabled={exporting}
                    onClick={() => setExporting(true)}
                  >
                    {t("downloadPdf")}
                  </Button>
                  <Button type="button" size="sm" variant="outline" onClick={() => window.print()}>
                    {t("printSchedule")}
                  </Button>
                </div>
              ) : null}
            </div>
            {canEdit && selected.length > 0 ? (
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
                columnClassName="w-20 min-w-20 max-w-20"
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
                      disabled={!canEdit || save.isPending}
                      onClick={() => {
                        if (canEdit) toggleCell(employee.id, date);
                      }}
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
                      {canEdit ? (
                      <Button
                        type="button"
                        size="sm"
                        variant="outline"
                        className="h-auto w-full whitespace-normal px-1 py-1 text-center text-xs"
                        onClick={() => openPattern(employee.id)}
                      >
                        {t("fillPattern")}
                      </Button>
                      ) : null}
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
          {grid.employees.length > 0 ? (
            <div
              ref={sheetRef}
              className={exporting ? "fixed top-0 left-[-10000px] w-[281mm] bg-white" : "hidden print:block"}
            >
              <style>{`@media print { @page { size: A4 landscape; margin: 8mm; } }`}</style>
              <ScheduleSheet
                start={grid.start}
                end={grid.end}
                employees={grid.employees}
                monthLabel={formatCrmMonth(period.month, locale)}
                title={t("schedulePlanTitle")}
              />
            </div>
          ) : null}
          </>
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
