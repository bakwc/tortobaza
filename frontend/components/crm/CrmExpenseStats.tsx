"use client";

import { useEffect, useRef, useState } from "react";
import { House, Users } from "lucide-react";
import { useTranslations } from "next-intl";
import { useCurrentUser } from "@/hooks/useAuth";
import { formatAedWhole } from "@/lib/format";
import { cn } from "@/lib/utils";

export function CrmExpenseStats({
  salary,
  rent,
  compact,
}: {
  salary: string | undefined;
  rent: string | undefined;
  compact: boolean;
}) {
  const currentUser = useCurrentUser();
  if (!currentUser.data?.is_staff) {
    return null;
  }
  if (salary === undefined || rent === undefined) {
    return null;
  }

  return <CrmExpenseBadge salary={salary} rent={rent} compact={compact} />;
}

function CrmExpenseBadge({
  salary,
  rent,
  compact,
}: {
  salary: string;
  rent: string;
  compact: boolean;
}) {
  const t = useTranslations("crm");
  const [hintOpen, setHintOpen] = useState(false);
  const rootRef = useRef<HTMLSpanElement>(null);
  const total = Number.parseFloat(salary) + Number.parseFloat(rent);
  const iconClass = compact ? "h-3 w-3" : "h-3.5 w-3.5";

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

  return (
    <span ref={rootRef} className="relative inline-flex">
      <span
        className={cn(
          "inline-flex shrink-0 items-center gap-1 rounded-lg border border-[var(--line)] bg-[var(--cream)] font-semibold tabular-nums text-[var(--ink)]",
          compact ? "px-1.5 py-0.5 text-xs" : "px-2.5 py-1 text-sm",
        )}
      >
        <button
          type="button"
          aria-label={t("expensesHint")}
          aria-expanded={hintOpen}
          className="inline-flex shrink-0"
          onClick={(event) => {
            event.preventDefault();
            event.stopPropagation();
            setHintOpen((open) => !open);
          }}
          onPointerDown={(event) => {
            event.stopPropagation();
          }}
        >
          {t("expenses")}
        </button>
        <span>{formatAedWhole(total)}</span>
        <span className="inline-flex items-center gap-0.5">
          <Users className={iconClass} />
          {formatAedWhole(salary)}
        </span>
        <span className="inline-flex items-center gap-0.5">
          <House className={iconClass} />
          {formatAedWhole(rent)}
        </span>
      </span>
      {hintOpen ? (
        <span
          className={cn(
            "absolute z-20 mt-1 w-56 rounded-lg border border-[var(--line)] bg-white px-2.5 py-2 text-left text-xs font-normal leading-snug text-[var(--ink)] shadow-md",
            compact ? "right-0 top-full" : "left-1/2 top-full -translate-x-1/2",
          )}
        >
          {t("expensesHint")}
        </span>
      ) : null}
    </span>
  );
}
