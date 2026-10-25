"use client";

import { useEffect, useRef, useState } from "react";
import { House, Users } from "lucide-react";
import { useTranslations } from "next-intl";
import { useCurrentUser } from "@/hooks/useAuth";
import type { CrmSalaryEmployee } from "@/lib/api/types";
import { formatAed, formatAedWhole } from "@/lib/format";
import { cn } from "@/lib/utils";

export function CrmExpenseStats({
  salary,
  rent,
  employees,
  compact,
  detailed,
}: {
  salary: string | undefined;
  rent: string | undefined;
  employees: CrmSalaryEmployee[] | undefined;
  compact: boolean;
  detailed: boolean;
}) {
  const currentUser = useCurrentUser();
  if (!currentUser.data?.is_finance_admin) {
    return null;
  }
  if (salary === undefined || rent === undefined || employees === undefined) {
    return null;
  }

  return (
    <CrmExpenseBadge
      salary={salary}
      rent={rent}
      employees={employees}
      compact={compact}
      detailed={detailed}
    />
  );
}

function CrmExpenseBadge({
  salary,
  rent,
  employees,
  compact,
  detailed,
}: {
  salary: string;
  rent: string;
  employees: CrmSalaryEmployee[];
  compact: boolean;
  detailed: boolean;
}) {
  const t = useTranslations("crm");
  const [detailsOpen, setDetailsOpen] = useState(false);
  const rootRef = useRef<HTMLSpanElement>(null);
  const total = Number.parseFloat(salary) + Number.parseFloat(rent);
  const iconClass = compact ? "h-3 w-3" : "h-3.5 w-3.5";

  useEffect(() => {
    if (!detailsOpen) {
      return;
    }
    const onPointerDown = (event: PointerEvent) => {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) {
        setDetailsOpen(false);
      }
    };
    document.addEventListener("pointerdown", onPointerDown);
    return () => document.removeEventListener("pointerdown", onPointerDown);
  }, [detailsOpen]);

  return (
    <span ref={rootRef} className="relative inline-flex">
      <button
        type="button"
        aria-expanded={detailsOpen}
        className={cn(
          "inline-flex shrink-0 items-center gap-1 rounded-lg border border-[var(--line)] bg-[var(--cream)] font-semibold tabular-nums text-[var(--ink)]",
          compact ? "px-1.5 py-0.5 text-xs" : "px-2.5 py-1 text-sm",
        )}
        onClick={(event) => {
          event.preventDefault();
          event.stopPropagation();
          setDetailsOpen((open) => !open);
        }}
        onPointerDown={(event) => {
          event.stopPropagation();
        }}
      >
        <span>{t("expenses")}</span>
        <span>{formatAedWhole(total)}</span>
        {detailed ? (
          <span className="inline-flex items-center gap-0.5">
            (
            <Users className={iconClass} />
            {formatAedWhole(salary)}
            <span>+</span>
            <House className={iconClass} />
            {formatAedWhole(rent)})
          </span>
        ) : null}
      </button>
      {detailsOpen ? (
        <span
          className={cn(
            "absolute z-20 mt-1 grid w-max min-w-56 grid-cols-[minmax(0,1fr)_auto_auto] gap-x-3 gap-y-1 rounded-lg border border-[var(--line)] bg-white px-2.5 py-2 text-left text-xs font-normal leading-snug text-[var(--ink)] shadow-md",
            compact ? "right-0 top-full" : "left-1/2 top-full -translate-x-1/2",
          )}
        >
          {employees.length > 0 ? (
            <>
              <span />
              <span className="font-medium text-[var(--muted-2)]">{t("salaryHours")}</span>
              <span className="font-medium text-[var(--muted-2)]">{t("salaryEarned")}</span>
            </>
          ) : null}
          {employees.map((employee) => (
            <span key={employee.id} className="contents">
              <span className="truncate">{employee.name}</span>
              <span className="tabular-nums">{employee.hours}</span>
              <span className="tabular-nums">{formatAed(employee.money)}</span>
            </span>
          ))}
          <span className={employees.length > 0 ? "col-span-2 border-t border-[var(--line)] pt-1" : "col-span-2"}>
            {t("expensesRent")}
          </span>
          <span
            className={cn(
              "tabular-nums",
              employees.length > 0 && "border-t border-[var(--line)] pt-1",
            )}
          >
            {formatAed(rent)}
          </span>
        </span>
      ) : null}
    </span>
  );
}
