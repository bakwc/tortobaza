"use client";

import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Spinner } from "@/components/ui/spinner";
import { cn } from "@/lib/utils";
import { formatTimeslot, formatTimeslotDateLabel } from "@/lib/format";
import type { CheckoutSchedule, FulfillmentType } from "@/lib/api/types";

export function TimeslotPicker({
  type,
  value,
  onChange,
}: {
  type: FulfillmentType;
  value: CheckoutSchedule | null;
  onChange: (v: CheckoutSchedule | null) => void;
}) {
  const [selectedDate, setSelectedDate] = useState<string | null>(null);

  const { data, isLoading, error } = useQuery({
    queryKey: ["fulfillment-options", type],
    queryFn: () => api.getFulfillmentOptions(type),
  });

  useEffect(() => {
    if (value?.mode === "slot") setSelectedDate(value.date);
  }, [value]);

  useEffect(() => {
    if (!data) return;
    if (value !== null) return;
    if (data.express_available) return;
    const d0 = data.dates[0];
    const s0 = d0?.slots[0];
    if (d0 && s0) {
      onChange({
        mode: "slot",
        date: d0.date,
        start_time: s0.start_time,
        end_time: s0.end_time,
      });
      setSelectedDate(d0.date);
    }
  }, [data, value, onChange]);

  useEffect(() => {
    if (!data?.dates.length) return;
    if (value?.mode !== "slot") return;
    if (selectedDate === null) {
      const first = data.dates[0]?.date;
      if (first !== undefined) setSelectedDate(first);
    }
  }, [data, value?.mode, selectedDate]);

  const dateEntry =
    data?.dates.find((d) => d.date === selectedDate) ?? data?.dates[0];
  const slots = dateEntry?.slots ?? [];
  const showScheduledPicker = value?.mode === "slot";

  return (
    <div className="space-y-4">
      {isLoading ? (
        <div className="flex items-center gap-2 text-sm text-[var(--ink)]/60">
          <Spinner /> Loading options…
        </div>
      ) : null}

      {error ? (
        <p className="text-sm text-[var(--danger)]">
          Could not load delivery options. Ensure your cart has items.
        </p>
      ) : null}

      {data && !data.express_available && data.dates.length === 0 ? (
        <p className="text-sm text-[var(--ink)]/60">No delivery windows available.</p>
      ) : null}

      {data && (data.express_available || data.dates.length > 0) ? (
        <>
          <p className="text-xs font-medium uppercase tracking-wide text-[var(--ink)]/50">
            How do you want delivery?
          </p>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {data.express_available ? (
              <button
                type="button"
                onClick={() => onChange({ mode: "express" })}
                className={cn(
                  "flex flex-col items-start rounded-2xl border px-4 py-4 text-left text-sm transition",
                  value?.mode === "express"
                    ? "border-[var(--brand)] bg-[var(--cream)]"
                    : "border-[var(--line)] bg-white hover:border-[var(--muted-2)]",
                )}
              >
                <span className="font-semibold text-[var(--ink)]">
                  Within 2 hours
                </span>
                <span className="mt-1 text-xs leading-snug text-[var(--ink)]/60">
                  As soon as possible after you place the order
                </span>
              </button>
            ) : null}
            {data.dates.length > 0 ? (
              <button
                type="button"
                onClick={() => {
                  const d0 = data.dates[0];
                  const first = d0.slots[0];
                  if (first) {
                    onChange({
                      mode: "slot",
                      date: d0.date,
                      start_time: first.start_time,
                      end_time: first.end_time,
                    });
                    setSelectedDate(d0.date);
                  }
                }}
                className={cn(
                  "flex flex-col items-start rounded-2xl border px-4 py-4 text-left text-sm transition",
                  value?.mode === "slot"
                    ? "border-[var(--brand)] bg-[var(--cream)]"
                    : "border-[var(--line)] bg-white hover:border-[var(--muted-2)]",
                )}
              >
                <span className="font-semibold text-[var(--ink)]">
                  Scheduled time
                </span>
                <span className="mt-1 text-xs leading-snug text-[var(--ink)]/60">
                  Pick a date and hour window
                </span>
              </button>
            ) : null}
          </div>

          {showScheduledPicker && data.dates.length ? (
            <>
              <div className="scrollbar-none -mx-1 flex gap-2 overflow-x-auto px-1">
                {data.dates.map((d) => (
                  <button
                    key={d.date}
                    type="button"
                    onClick={() => {
                      setSelectedDate(d.date);
                      const first = d.slots[0];
                      if (first) {
                        onChange({
                          mode: "slot",
                          date: d.date,
                          start_time: first.start_time,
                          end_time: first.end_time,
                        });
                      }
                    }}
                    className={cn(
                      "shrink-0 rounded-full border px-4 py-2 text-sm",
                      (selectedDate ?? dateEntry?.date) === d.date
                        ? "border-[var(--brand)] bg-[var(--brand)] text-[var(--brand-foreground)]"
                        : "border-[var(--line)] bg-white text-[var(--ink)] hover:border-[var(--muted-2)]",
                    )}
                  >
                    {formatTimeslotDateLabel(d.date)}
                  </button>
                ))}
              </div>

              {slots.length > 0 ? (
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                  {slots.map((slot) => (
                    <button
                      key={`${slot.start_time}-${slot.end_time}`}
                      type="button"
                      onClick={() => {
                        const d = dateEntry?.date ?? selectedDate;
                        if (!d) return;
                        onChange({
                          mode: "slot",
                          date: d,
                          start_time: slot.start_time,
                          end_time: slot.end_time,
                        });
                      }}
                      className={cn(
                        "rounded-2xl border px-3 py-2 text-sm transition",
                        value?.mode === "slot" &&
                          value.date === (dateEntry?.date ?? selectedDate) &&
                          value.start_time === slot.start_time &&
                          value.end_time === slot.end_time
                          ? "border-[var(--brand)] bg-[var(--cream)]"
                          : "border-[var(--line)] bg-white hover:border-[var(--muted-2)]",
                      )}
                    >
                      {formatTimeslot(slot.start_time, slot.end_time)}
                    </button>
                  ))}
                </div>
              ) : null}
            </>
          ) : null}
        </>
      ) : null}
    </div>
  );
}
