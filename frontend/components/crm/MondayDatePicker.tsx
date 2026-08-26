"use client";

import { useEffect, useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { Calendar, ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  daysInUtcMonth,
  formatCrmDate,
  formatCrmMonthYear,
  mondayFirstOffset,
  mondayFirstWeekdayLabels,
  parseIsoDateParts,
  toIsoDate,
} from "@/lib/format";
import { cn } from "@/lib/utils";

function shiftMonth(year: number, month: number, delta: number): { year: number; month: number } {
  const next = new Date(Date.UTC(year, month - 1 + delta, 1));
  return { year: next.getUTCFullYear(), month: next.getUTCMonth() + 1 };
}

export function MondayDatePicker({
  value,
  onChange,
}: {
  value: string;
  onChange: (iso: string) => void;
}) {
  const locale = useLocale();
  const t = useTranslations("crm");
  const [open, setOpen] = useState(false);
  const parsed = parseIsoDateParts(value);
  const [viewYear, setViewYear] = useState(parsed.year);
  const [viewMonth, setViewMonth] = useState(parsed.month);

  useEffect(() => {
    setViewYear(parsed.year);
    setViewMonth(parsed.month);
  }, [parsed.year, parsed.month]);

  const labels = mondayFirstWeekdayLabels(locale);
  const offset = mondayFirstOffset(viewYear, viewMonth);
  const dayCount = daysInUtcMonth(viewYear, viewMonth);
  const cells: (number | null)[] = [
    ...Array.from({ length: offset }, () => null),
    ...Array.from({ length: dayCount }, (_, i) => i + 1),
  ];
  while (cells.length % 7 !== 0) {
    cells.push(null);
  }

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        className="flex w-full items-center gap-2 rounded-2xl border border-[var(--line)] bg-white px-4 py-3 text-left text-sm font-medium text-[var(--ink)] hover:border-[var(--brand)]/40"
        aria-expanded={open}
      >
        <Calendar className="h-4 w-4 shrink-0 text-[var(--brand)]" />
        <span>{formatCrmDate(value, locale)}</span>
      </button>

      {open ? (
        <div className="absolute z-20 mt-2 w-full min-w-[280px] rounded-2xl border border-[var(--line)] bg-white p-3 shadow-lg">
          <div className="mb-3 flex items-center justify-between gap-2">
            <Button
              type="button"
              variant="ghost"
              size="icon"
              onClick={() => {
                const next = shiftMonth(viewYear, viewMonth, -1);
                setViewYear(next.year);
                setViewMonth(next.month);
              }}
              aria-label={t("prevMonth")}
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <span className="text-sm font-semibold capitalize text-[var(--ink)]">
              {formatCrmMonthYear(viewYear, viewMonth, locale)}
            </span>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              onClick={() => {
                const next = shiftMonth(viewYear, viewMonth, 1);
                setViewYear(next.year);
                setViewMonth(next.month);
              }}
              aria-label={t("nextMonth")}
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
          <div className="grid grid-cols-7 gap-1 text-center text-[11px] font-semibold uppercase tracking-wide text-[var(--muted-2)]">
            {labels.map((label, index) => (
              <div key={`${label}-${index}`}>{label}</div>
            ))}
          </div>
          <div className="mt-1 grid grid-cols-7 gap-1">
            {cells.map((day, index) => {
              if (day === null) {
                return <div key={`empty-${index}`} />;
              }
              const iso = toIsoDate(viewYear, viewMonth, day);
              const selected = iso === value;
              return (
                <button
                  key={iso}
                  type="button"
                  onClick={() => {
                    onChange(iso);
                    setOpen(false);
                  }}
                  className={cn(
                    "flex h-9 items-center justify-center rounded-full text-sm",
                    selected
                      ? "bg-[var(--brand)] font-semibold text-white"
                      : "text-[var(--ink)] hover:bg-[var(--cream)]",
                  )}
                >
                  {day}
                </button>
              );
            })}
          </div>
        </div>
      ) : null}
    </div>
  );
}
