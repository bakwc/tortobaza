"use client";

import { Clock, Truck } from "lucide-react";
import { useTranslations } from "next-intl";
import { formatPrepTime, formatTimeSlot } from "@/lib/format";

export function CrmOrderTimeSlot({
  timeStart,
  timeEnd,
  whenReady,
  layout,
}: {
  timeStart: string | null;
  timeEnd: string | null;
  whenReady: boolean;
  layout: "day" | "month";
}) {
  const t = useTranslations("crm");
  const compact = layout === "month";
  const slot = formatTimeSlot(
    timeStart,
    timeEnd,
    whenReady,
    t("timeUnknown"),
    t("timeWhenReady"),
  );
  const prepLabel =
    layout === "day" && !whenReady && timeStart !== null
      ? t("prepareBy", { time: formatPrepTime(timeStart) })
      : null;

  return (
    <span className="inline-flex min-w-0 items-center gap-1.5">
      <Clock
        className={
          compact
            ? "h-3.5 w-3.5 shrink-0 text-[var(--brand)]"
            : "h-4 w-4 shrink-0 text-[var(--brand)] lg:h-5 lg:w-5"
        }
      />
      <span
        className={
          compact
            ? "min-w-0 truncate text-sm font-semibold text-[var(--ink)]"
            : "text-lg font-bold tracking-tight text-[var(--ink)] lg:text-2xl"
        }
      >
        {slot}
      </span>
      {layout === "month" ? <Truck className="h-3.5 w-3.5 shrink-0" /> : null}
      {prepLabel !== null ? (
        <span
          className={
            compact
              ? "shrink-0 text-xs font-medium text-[var(--muted-2)]"
              : "shrink-0 text-sm font-medium text-[var(--muted-2)] lg:text-base"
          }
        >
          {prepLabel}
        </span>
      ) : null}
    </span>
  );
}
