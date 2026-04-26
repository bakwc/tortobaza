"use client";

import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Spinner } from "@/components/ui/spinner";
import { cn } from "@/lib/utils";
import {
  formatTimeslot,
  formatTimeslotDateLabel,
  todayIsoDate,
} from "@/lib/format";
import type { FulfillmentType } from "@/lib/api/types";

const DAYS_AHEAD = 7;

function nextDates(): string[] {
  const today = new Date();
  const result: string[] = [];
  for (let i = 0; i < DAYS_AHEAD; i++) {
    const d = new Date(today);
    d.setDate(d.getDate() + i);
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    result.push(`${y}-${m}-${day}`);
  }
  return result;
}

export function TimeslotPicker({
  type,
  value,
  onChange,
}: {
  type: FulfillmentType;
  value: number | null;
  onChange: (id: number) => void;
}) {
  const [date, setDate] = useState(todayIsoDate());
  const dates = nextDates();

  const { data, isLoading, error } = useQuery({
    queryKey: ["timeslots", date, type],
    queryFn: () => api.getDeliveryTimeslots(date, type),
  });

  useEffect(() => {
    if (!value && data && data.length > 0) {
      const firstAvailable = data.find((s) => s.remaining_capacity > 0);
      if (firstAvailable) onChange(firstAvailable.id);
    }
  }, [data, value, onChange]);

  return (
    <div className="space-y-4">
      <div className="scrollbar-none -mx-1 flex gap-2 overflow-x-auto px-1">
        {dates.map((d) => (
          <button
            key={d}
            type="button"
            onClick={() => setDate(d)}
            className={cn(
              "shrink-0 rounded-full border px-4 py-2 text-sm",
              date === d
                ? "border-[var(--brand)] bg-[var(--brand)] text-[var(--brand-foreground)]"
                : "border-[var(--line)] bg-white text-[var(--ink)] hover:border-[var(--muted-2)]",
            )}
          >
            {formatTimeslotDateLabel(d)}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="flex items-center gap-2 text-sm text-[var(--ink)]/60">
          <Spinner /> Loading timeslots…
        </div>
      ) : null}

      {error ? (
        <p className="text-sm text-[var(--danger)]">Could not load timeslots.</p>
      ) : null}

      {data && data.length === 0 ? (
        <p className="text-sm text-[var(--ink)]/60">
          No slots available on this date — please choose another day.
        </p>
      ) : null}

      {data && data.length > 0 ? (
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
          {data.map((slot) => {
            const disabled = slot.remaining_capacity <= 0;
            return (
              <button
                key={slot.id}
                type="button"
                disabled={disabled}
                onClick={() => onChange(slot.id)}
                className={cn(
                  "rounded-2xl border px-3 py-2 text-sm transition",
                  value === slot.id
                    ? "border-[var(--brand)] bg-[var(--cream)]"
                    : "border-[var(--line)] bg-white hover:border-[var(--muted-2)]",
                  disabled &&
                    "cursor-not-allowed opacity-50 hover:border-[var(--line)]",
                )}
              >
                <span className="block">
                  {formatTimeslot(slot.start_time, slot.end_time)}
                </span>
                {disabled ? (
                  <span className="block text-xs text-[var(--danger)]">Sold out</span>
                ) : null}
              </button>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}
