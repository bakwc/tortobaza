"use client";

import { type ReactNode } from "react";
import { useLocale, useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Link } from "@/i18n/navigation";
import { formatCrmCompactDate, formatCrmDate } from "@/lib/format";
import { cn } from "@/lib/utils";

const BUSINESS_TIMEZONE = "Asia/Tbilisi";

export type RsgeToneName = "pending" | "confirmed" | "rejected" | "neutral";

export type RsgeTone = {
  card: string;
  accent: string;
  media: string;
  chip: string;
  amount: string;
};

export type RsgeColumn = {
  label: string;
  align: "left" | "right";
};

const TONES: Record<RsgeToneName, RsgeTone> = {
  pending: {
    card: "border-amber-200 bg-amber-50/60",
    accent: "border-l-amber-400",
    media: "border-amber-200 bg-white/70 text-amber-600",
    chip: "bg-amber-100 text-amber-800",
    amount: "text-[var(--ink)]",
  },
  confirmed: {
    card: "border-emerald-200 bg-emerald-50/50",
    accent: "border-l-emerald-400",
    media: "border-emerald-200 bg-white/70 text-emerald-600",
    chip: "bg-emerald-100 text-emerald-800",
    amount: "text-[var(--ink)]",
  },
  rejected: {
    card: "border-rose-200 bg-rose-50/50",
    accent: "border-l-rose-400",
    media: "border-rose-200 bg-white/70 text-rose-600",
    chip: "bg-rose-100 text-rose-800",
    amount: "text-[var(--ink)]",
  },
  neutral: {
    card: "border-[var(--line)] bg-white",
    accent: "border-l-[var(--line)]",
    media: "border-[var(--line)] bg-white/70 text-[var(--muted-2)]",
    chip: "bg-[var(--cream)] text-[var(--ink)]",
    amount: "text-[var(--ink)]",
  },
};

export function rsgeTone(name: RsgeToneName): RsgeTone {
  return TONES[name];
}

export function rsgeDateKey(iso: string): string {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: BUSINESS_TIMEZONE,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date(iso));
}

export function rsgeMonth(iso: string): string {
  return rsgeDateKey(iso).slice(0, 7);
}

export function sumGel(values: string[]): number {
  const cents = values.reduce((sum, value) => sum + Math.round(Number.parseFloat(value) * 100), 0);
  return cents / 100;
}

export function groupRsgeByDate<T>(
  items: T[],
  dateOf: (item: T) => string,
  pending: (item: T) => boolean,
): { date: string; items: T[] }[] {
  const groups: { date: string; items: T[] }[] = [];
  for (const item of items) {
    const date = dateOf(item);
    const existing = groups.find((group) => group.date === date);
    if (existing) existing.items.push(item);
    else groups.push({ date, items: [item] });
  }
  for (const group of groups) {
    const waiting: T[] = [];
    const rest: T[] = [];
    for (const item of group.items) {
      if (pending(item)) waiting.push(item);
      else rest.push(item);
    }
    group.items = [...waiting, ...rest];
  }
  return groups;
}

export function RsgeEmpty({ children }: { children: ReactNode }) {
  return (
    <div className="rounded-3xl border border-[var(--line)] bg-white p-8 text-center text-sm text-[var(--muted-2)] shadow-sm">
      {children}
    </div>
  );
}

export function RsgeSummary({
  count,
  total,
  pending,
}: {
  count: number;
  total: string;
  pending: number;
}) {
  const t = useTranslations("rsge");
  return (
    <div className="grid grid-cols-3 rounded-2xl border border-[var(--line)] bg-white px-2 py-3 shadow-sm md:px-4">
      <RsgeFigure label={t("summaryCount")} value={String(count)} className="text-[var(--ink)]" />
      <RsgeFigure label={t("summaryTotal")} value={total} className="text-[var(--ink)]" />
      <RsgeFigure
        label={t("summaryPending")}
        value={String(pending)}
        className={pending > 0 ? "text-amber-700" : "text-[var(--ink)]"}
      />
    </div>
  );
}

export function RsgeDayHeader({ date, count, sum }: { date: string; count: number; sum: string }) {
  const locale = useLocale();
  return (
    <div className="flex items-baseline justify-between gap-3 px-1 text-[var(--ink)]">
      <span className="min-w-0 truncate text-sm font-semibold md:text-base">
        <span className="md:hidden">{formatCrmCompactDate(date, locale)}</span>
        <span className="hidden md:inline">{formatCrmDate(date, locale)}</span>
      </span>
      <span className="flex shrink-0 items-baseline gap-2 text-xs font-medium text-[var(--muted-2)]">
        <span>{count}</span>
        <span className="text-[var(--ink)]">{sum}</span>
      </span>
    </div>
  );
}

export function RsgeChip({
  className,
  href,
  children,
}: {
  className: string;
  href: string | null;
  children: ReactNode;
}) {
  const chipClass = cn(
    "flex shrink-0 items-center gap-1 rounded-full px-1.5 py-0.5 text-[10px] font-semibold",
    href !== null && "hover:opacity-90",
    className,
  );
  if (href !== null) {
    return (
      <Link href={href} onClick={(event) => event.stopPropagation()} className={chipClass}>
        {children}
      </Link>
    );
  }
  return <span className={chipClass}>{children}</span>;
}

export function RsgeDocumentRow({
  id,
  tone,
  icon,
  title,
  subtitle,
  amount,
  chips,
  onConfirm,
  onReject,
  details,
  columns,
  rowKeys,
  rows,
}: {
  id: string;
  tone: RsgeTone;
  icon: ReactNode;
  title: string;
  subtitle: string;
  amount: string;
  chips: ReactNode;
  onConfirm: (() => void) | null;
  onReject: (() => void) | null;
  details: ReactNode | null;
  columns: RsgeColumn[];
  rowKeys: number[];
  rows: string[][];
}) {
  const t = useTranslations("rsge");
  const pending = onConfirm !== null && onReject !== null;

  return (
    <div
      id={id}
      className={cn("grid gap-3 rounded-2xl border border-l-4 p-3 shadow-sm md:p-4", tone.card, tone.accent)}
    >
      <div className="flex min-w-0 items-center gap-2 md:gap-3">
        <div
          className={cn(
            "flex h-8 w-8 shrink-0 items-center justify-center rounded-md border md:h-10 md:w-10 md:rounded-lg",
            tone.media,
          )}
        >
          {icon}
        </div>
        <p className="min-w-0 flex-1 truncate text-xs text-[var(--muted-2)] md:text-sm">
          <span className="font-semibold text-[var(--ink)]">{title}</span>
          {subtitle !== "" ? (
            <>
              <span className="mx-1">·</span>
              <span>{subtitle}</span>
            </>
          ) : null}
        </p>
        <span className={cn("shrink-0 text-sm font-bold", tone.amount)}>{amount}</span>
      </div>
      <div className="flex min-w-0 flex-wrap items-center gap-1.5">{chips}</div>
      {details}
      {rows.length > 0 ? <RsgeGoodsTable columns={columns} rowKeys={rowKeys} rows={rows} /> : null}
      {pending ? (
        <div className="flex justify-end gap-2 border-t border-black/5 pt-3">
          <Button type="button" size="sm" onClick={onConfirm}>
            {t("confirm")}
          </Button>
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={onReject}
            className="text-[var(--danger)] hover:bg-rose-50"
          >
            {t("reject")}
          </Button>
        </div>
      ) : null}
    </div>
  );
}

function RsgeFigure({ label, value, className }: { label: string; value: string; className: string }) {
  return (
    <div className="min-w-0 px-1 text-center">
      <p className="text-[10px] font-semibold uppercase tracking-wide text-[var(--muted-2)]">{label}</p>
      <p className={cn("mt-1 text-sm font-bold tabular-nums md:text-base", className)}>{value}</p>
    </div>
  );
}

function RsgeGoodsTable({
  columns,
  rowKeys,
  rows,
}: {
  columns: RsgeColumn[];
  rowKeys: number[];
  rows: string[][];
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[36rem] text-sm">
        <thead>
          <tr className="border-b border-black/5 text-[10px] uppercase tracking-wide text-[var(--muted-2)]">
            {columns.map((column) => (
              <th
                key={column.label}
                className={cn(
                  "px-2 py-1.5 font-medium first:pl-0 last:pr-0",
                  column.align === "right" ? "text-right" : "text-left",
                )}
              >
                {column.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={rowKeys[index]} className="border-t border-black/5">
              {row.map((cell, cellIndex) => (
                <td
                  key={columns[cellIndex].label}
                  className={cn(
                    "px-2 py-1.5 text-[var(--ink)] first:pl-0 last:pr-0",
                    columns[cellIndex].align === "right" && "whitespace-nowrap text-right tabular-nums",
                  )}
                >
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
