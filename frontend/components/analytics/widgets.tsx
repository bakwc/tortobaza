"use client";

import type { ReactElement, ReactNode } from "react";
import { ResponsiveContainer } from "recharts";
import { formatAmount, formatMoney } from "@/lib/format";

export const COLOR_ORDERS = "#5b8fa8";
export const COLOR_REVENUE = "#cc767f";
export const COLOR_NEW = "#3f6b58";
export const COLOR_USUAL = "#666666";
export const COLOR_HEAVY = "#b34a3a";
export const AXIS_TICK = { fontSize: 12, fill: "#666666" };
export const TOOLTIP_STYLE = { borderRadius: 12, borderColor: "#e8ddcd", fontSize: 13 };

export function ChartFrame({ children }: { children: ReactElement }) {
  return (
    <div className="h-72 w-full min-w-0">
      <ResponsiveContainer width="100%" height="100%">
        {children}
      </ResponsiveContainer>
    </div>
  );
}

export function Metric({ label, value, hint }: { label: string; value: string; hint: string | null }) {
  return (
    <article className="rounded-2xl border border-[var(--line)] bg-white p-4">
      <p className="text-xs font-medium uppercase tracking-wide text-[var(--muted)]">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-[var(--ink)]">{value}</p>
      {hint ? <p className="mt-1 text-sm text-[var(--price)]">{hint}</p> : null}
    </article>
  );
}

export function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="grid gap-4 rounded-3xl border border-[var(--line)] bg-white p-6">
      <h2 className="text-lg font-semibold text-[var(--ink)]">{title}</h2>
      {children}
    </section>
  );
}

export function Note({ children }: { children: ReactNode }) {
  return <p className="text-sm text-[var(--price)]">{children}</p>;
}

export function deltaText(current: string | number, previous: string | number, money: boolean): string {
  const diff = Number(current) - Number(previous);
  const amount = money ? formatMoney(diff, "GEL") : formatAmount(diff);
  const signed = diff > 0 ? `+${amount}` : amount;
  if (Number(previous) === 0) return signed;
  const percent = (diff / Number(previous)) * 100;
  const percentText = `${percent > 0 ? "+" : ""}${percent.toFixed(0)}%`;
  return `${signed} · ${percentText}`;
}

function localeTag(locale: string): string {
  if (locale === "ka") return "ka-GE";
  if (locale === "ru") return "ru-RU";
  return "en-GB";
}

export function dayLabel(value: string, locale: string): string {
  const [year, month, day] = value.split("-");
  return new Intl.DateTimeFormat(localeTag(locale), {
    day: "numeric",
    month: "short",
    timeZone: "UTC",
  }).format(new Date(Date.UTC(Number(year), Number(month) - 1, Number(day))));
}

export function monthLabel(month: string, locale: string): string {
  const [year, mon] = month.split("-");
  return new Intl.DateTimeFormat(localeTag(locale), {
    month: "short",
    year: "2-digit",
    timeZone: "UTC",
  }).format(new Date(Date.UTC(Number(year), Number(mon) - 1, 1)));
}
