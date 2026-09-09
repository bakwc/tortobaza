"use client";

import { useEffect, useRef, useState } from "react";
import { Clock, Info, Truck, Utensils } from "lucide-react";
import { useTranslations } from "next-intl";
import { formatPrepTime, formatTimeSlot } from "@/lib/format";
import { cn } from "@/lib/utils";

export function CrmOrderTimeSlot({
  timeStart,
  timeEnd,
  whenReady,
  compact,
}: {
  timeStart: string | null;
  timeEnd: string | null;
  whenReady: boolean;
  compact: boolean;
}) {
  const t = useTranslations("crm");
  const [hintOpen, setHintOpen] = useState(false);
  const rootRef = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    if (!hintOpen) {
      return;
    }
    const onPointerDown = (event: PointerEvent) => {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) {
        setHintOpen(false);
      }
    };
    document.addEventListener("pointerdown", onPointerDown);
    return () => document.removeEventListener("pointerdown", onPointerDown);
  }, [hintOpen]);

  if (whenReady || !timeStart) {
    return (
      <span className="flex items-center gap-1.5">
        <Clock
          className={
            compact
              ? "h-3.5 w-3.5 shrink-0 text-[var(--brand)]"
              : "h-4 w-4 text-[var(--brand)] lg:h-5 lg:w-5"
          }
        />
        <span
          className={
            compact
              ? "truncate text-sm font-semibold text-[var(--ink)]"
              : "text-lg font-bold tracking-tight text-[var(--ink)] lg:text-2xl"
          }
        >
          {formatTimeSlot(
            timeStart,
            timeEnd,
            whenReady,
            t("timeUnknown"),
            t("timeWhenReady"),
          )}
        </span>
      </span>
    );
  }

  const prep = formatPrepTime(timeStart);
  const delivery = formatTimeSlot(
    timeStart,
    timeEnd,
    false,
    t("timeUnknown"),
    t("timeWhenReady"),
  );

  return (
    <span ref={rootRef} className="relative inline-flex min-w-0 items-center">
      <span
        className={cn(
          "inline-flex min-w-0 items-center gap-1.5",
          compact ? "text-sm font-semibold text-[var(--ink)]" : "",
        )}
      >
        <Utensils className="h-3.5 w-3.5 shrink-0 text-amber-900" />
        <span
          className={
            compact
              ? "tabular-nums"
              : "text-lg font-bold tracking-tight text-[var(--ink)] lg:text-2xl"
          }
        >
          {prep}
        </span>
        <Truck className="h-3.5 w-3.5 shrink-0" />
        <span
          className={
            compact
              ? "min-w-0 truncate tabular-nums"
              : "text-lg font-bold tracking-tight text-[var(--ink)] lg:text-2xl"
          }
        >
          {delivery}
        </span>
        <button
          type="button"
          aria-label={t("timeSlotHint")}
          aria-expanded={hintOpen}
          className="inline-flex shrink-0 text-[var(--muted-2)]"
          onClick={(event) => {
            event.preventDefault();
            event.stopPropagation();
            setHintOpen((open) => !open);
          }}
          onPointerDown={(event) => {
            event.stopPropagation();
          }}
        >
          <Info className={compact ? "h-3 w-3" : "h-3.5 w-3.5"} />
        </button>
      </span>
      {hintOpen ? (
        <span
          className={cn(
            "absolute z-20 mt-1 w-56 rounded-lg border border-[var(--line)] bg-white px-2.5 py-2 text-left text-xs font-normal leading-snug text-[var(--ink)] shadow-md",
            compact ? "right-0 top-full" : "left-1/2 top-full -translate-x-1/2",
          )}
        >
          {t("timeSlotHint")}
        </span>
      ) : null}
    </span>
  );
}
