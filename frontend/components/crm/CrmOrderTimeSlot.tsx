"use client";

import { Clock, Truck } from "lucide-react";
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
  const clockClass = compact
    ? "h-3.5 w-3.5 shrink-0 text-[var(--brand)]"
    : "h-4 w-4 shrink-0 text-[var(--brand)] lg:h-5 lg:w-5";
  const isUnset = whenReady || timeStart === null;
  const showSlot = showDeliveryTime || (showCookingTime && isUnset);
  const showPrep =
    showCookingTime && timeStart !== null && !whenReady && (layout === "day" || !showDeliveryTime);
  const prepTime =
    showPrep && timeStart !== null ? formatPrepTime(timeStart, deliveryDurationSeconds) : null;

  if (!showSlot && prepTime === null) return null;

  return (
    <span className="inline-flex min-w-0 items-center gap-1.5">
      {showSlot ? (
        <>
          <Clock className={clockClass} />
          <span className={timeClass}>{slot}</span>
          {compact && showDeliveryTime ? <Truck className="h-3.5 w-3.5 shrink-0" /> : null}
        </>
      ) : null}
      {prepTime !== null && compact ? (
        <>
          <Clock className={clockClass} />
          <span className={timeClass}>
            {t.rich("prepareBy", {
              time: () => <span>{prepTime}</span>,
            })}
          </span>
        </>
      ) : null}
      {prepTime !== null && !compact ? (
        <span className="inline-flex shrink-0 items-baseline gap-1.5 text-sm font-medium text-[var(--muted-2)] lg:text-base">
          {t.rich("prepareBy", {
            time: () => <span className={timeClass}>{prepTime}</span>,
          })}
        </span>
      ) : null}
    </span>
  );
}
