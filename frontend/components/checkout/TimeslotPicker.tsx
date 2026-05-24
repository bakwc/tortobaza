"use client";

import { useEffect, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { api } from "@/lib/api";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { cn } from "@/lib/utils";
import { formatTimeslot, formatTimeslotDateLabel } from "@/lib/format";
import { useCart } from "@/hooks/useCart";
import type { CheckoutSchedule, FulfillmentType } from "@/lib/api/types";

export function TimeslotPicker({
  type: _fulfillmentType,
  value,
  onChange,
}: {
  type: FulfillmentType;
  value: CheckoutSchedule | null;
  onChange: (v: CheckoutSchedule | null) => void;
}) {
  const locale = useLocale();
  const t = useTranslations("checkout");
  const { data: cart } = useCart();

  const cartFingerprint = useMemo(
    () =>
      cart?.items
        .map((item) => `${item.product.id}:${item.quantity}`)
        .sort()
        .join("|") ?? "",
    [cart?.items],
  );

  const { data, isLoading, error } = useQuery({
    queryKey: ["fulfillment-options", _fulfillmentType, cart?.updated_at, cartFingerprint],
    queryFn: () => api.getFulfillmentOptions(_fulfillmentType),
    enabled: Boolean(cart?.items.length),
    staleTime: 0,
    refetchOnWindowFocus: true,
  });

  const availableDates = useMemo(
    () => new Set(data?.dates.map((d) => d.date) ?? []),
    [data?.dates],
  );

  useEffect(() => {
    if (!data?.dates.length) return;
    if (value?.mode === "slot" && availableDates.has(value.date)) return;

    const d0 = data.dates[0];
    const s0 = d0?.slots[0];
    if (!d0 || !s0) return;

    onChange({
      mode: "slot",
      date: d0.date,
      start_time: s0.start_time,
      end_time: s0.end_time,
    });
  }, [data, value, onChange, availableDates]);

  const activeDate =
    value?.date && availableDates.has(value.date) ? value.date : data?.dates[0]?.date;
  const dateEntry =
    data?.dates.find((d) => d.date === activeDate) ?? data?.dates[0];
  const slots = dateEntry?.slots ?? [];

  return (
    <div className="min-w-0 space-y-4">
      {isLoading ? (
        <div className="flex items-center gap-2 text-sm text-[var(--ink)]/60">
          <Spinner /> {t("timeslotLoading")}
        </div>
      ) : null}

      {error ? <p className="text-sm text-[var(--danger)]">{t("timeslotError")}</p> : null}

      {data && data.dates.length === 0 ? (
        <p className="text-sm text-[var(--ink)]/60">{t("timeslotNoWindows")}</p>
      ) : null}

      {data && data.dates.length > 0 ? (
        <>
          <div className="space-y-2">
            <label
              htmlFor="checkout-schedule-date"
              className="text-xs font-medium uppercase tracking-wide text-[var(--ink)]/50"
            >
              {t("dateLabel")}
            </label>
            <Input
              id="checkout-schedule-date"
              type="date"
              min={data.dates[0].date}
              max={data.dates[data.dates.length - 1].date}
              value={activeDate ?? ""}
              onChange={(e) => {
                const date = e.target.value;
                if (!date) return;
                const entry = data.dates.find((d) => d.date === date);
                if (!entry) return;
                const first = entry.slots[0];
                if (first) {
                  onChange({
                    mode: "slot",
                    date,
                    start_time: first.start_time,
                    end_time: first.end_time,
                  });
                }
              }}
              className="max-w-xs rounded-2xl [&::-webkit-calendar-picker-indicator]:cursor-pointer"
            />
            {activeDate ? (
              <p className="text-sm text-[var(--ink)]/60">
                {formatTimeslotDateLabel(activeDate, locale)}
              </p>
            ) : null}
          </div>

          {slots.length > 0 ? (
            <div className="grid grid-cols-3 gap-2 sm:grid-cols-4 md:grid-cols-6">
              {slots.map((slot) => (
                <button
                  key={`${slot.start_time}-${slot.end_time}`}
                  type="button"
                  onClick={() => {
                    const d = dateEntry?.date ?? activeDate;
                    if (!d) return;
                    onChange({
                      mode: "slot",
                      date: d,
                      start_time: slot.start_time,
                      end_time: slot.end_time,
                    });
                  }}
                  className={cn(
                    "min-w-0 rounded-xl border px-1.5 py-2 text-center text-xs transition sm:px-2 sm:text-sm",
                    value?.date === (dateEntry?.date ?? activeDate) &&
                      value?.start_time === slot.start_time &&
                      value?.end_time === slot.end_time
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
    </div>
  );
}
