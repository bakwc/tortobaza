"use client";

import { useTranslations } from "next-intl";
import { formatPrepTime, formatTimeSlot } from "@/lib/format";

export function CrmOrderTimeSlot({
  timeStart,
  timeEnd,
  whenReady,
  deliveryDurationSeconds,
  layout,
  showDeliveryTime,
  showCookingTime,
}: {
  timeStart: string | null;
  timeEnd: string | null;
  whenReady: boolean;
  deliveryDurationSeconds: number | null;
  layout: "day" | "month";
  showDeliveryTime: boolean;
  showCookingTime: boolean;
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
  const timeClass = compact
    ? "min-w-0 truncate text-sm font-semibold text-[var(--ink)]"
    : "text-lg font-bold tracking-tight text-[var(--ink)] lg:text-2xl";
  const labelClass = compact
    ? "shrink-0 text-[10px] font-normal text-[var(--muted-2)]"
    : "shrink-0 text-xs font-medium text-[var(--muted-2)] lg:text-sm";
  const isUnset = whenReady || timeStart === null;
  const showSlot = showDeliveryTime || (showCookingTime && isUnset);
  const showPrep = showCookingTime && timeStart !== null && !whenReady;
  const prepTime =
    showPrep && timeStart !== null ? formatPrepTime(timeStart, deliveryDurationSeconds) : null;
  const showDeliverLabel = showDeliveryTime && !isUnset;

  if (!showSlot && prepTime === null) return null;

  return (
    <span className="inline-flex min-w-0 items-baseline gap-1.5">
      {prepTime !== null ? (
        <span className="inline-flex shrink-0 items-baseline gap-1">
          <span className={timeClass}>{prepTime}</span>
          <span className={labelClass}>{t("prepareLabel")}</span>
        </span>
      ) : null}
      {showSlot ? (
        <span className="inline-flex min-w-0 items-baseline gap-1">
          <span className={timeClass}>{slot}</span>
          {showDeliverLabel ? <span className={labelClass}>{t("deliverLabel")}</span> : null}
        </span>
      ) : null}
    </span>
  );
}
