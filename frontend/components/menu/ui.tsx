"use client";

import type { ReactNode, SelectHTMLAttributes } from "react";
import { useTranslations } from "next-intl";
import { Spinner } from "@/components/ui/spinner";
import { ApiError } from "@/lib/api/client";
import { cn } from "@/lib/utils";

export function Field({
  label,
  children,
  className,
}: {
  label: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <label className={cn("flex flex-col gap-1.5", className)}>
      <span className="text-xs font-medium uppercase tracking-wide text-[var(--ink)]/60">{label}</span>
      {children}
    </label>
  );
}

export function NativeSelect({ className, ...props }: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      {...props}
      className={cn(
        "h-12 w-full rounded-full border border-[var(--line)] bg-white px-5 text-sm text-[var(--ink)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--brand)]/30",
        className,
      )}
    />
  );
}

export function CheckboxField({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (value: boolean) => void;
}) {
  return (
    <label className="flex cursor-pointer items-center gap-2 text-sm text-[var(--ink)]">
      <input
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
        className="h-4 w-4 accent-[var(--brand)]"
      />
      {label}
    </label>
  );
}

export function Card({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <section className={cn("rounded-3xl border border-[var(--line)] bg-white p-6 shadow-sm", className)}>
      {children}
    </section>
  );
}

export function CardTitle({ children }: { children: ReactNode }) {
  return (
    <h2 className="text-sm font-semibold uppercase tracking-wide text-[var(--ink)]/50">{children}</h2>
  );
}

function collectMessages(value: unknown, out: string[]): void {
  if (typeof value === "string") {
    out.push(value);
    return;
  }
  if (Array.isArray(value)) {
    for (const item of value) collectMessages(item, out);
    return;
  }
  if (value && typeof value === "object") {
    for (const item of Object.values(value)) collectMessages(item, out);
  }
}

export function apiErrorMessage(error: unknown, fallback: string): string | null {
  if (!error) return null;
  if (error instanceof ApiError) {
    const messages: string[] = [];
    collectMessages(error.parsed(), messages);
    return messages.length > 0 ? messages.join(" ") : fallback;
  }
  return fallback;
}

export function ErrorText({ error }: { error: unknown }) {
  const t = useTranslations("stock");
  const message = apiErrorMessage(error, t("saveError"));
  if (!message) return null;
  return <p className="text-sm text-[var(--danger)]">{message}</p>;
}

export function LoadingBlock() {
  return (
    <div className="flex min-h-[30vh] items-center justify-center">
      <Spinner className="h-6 w-6 text-[var(--brand)]" />
    </div>
  );
}

export function QueryState({
  isLoading,
  isError,
  children,
}: {
  isLoading: boolean;
  isError: boolean;
  children: ReactNode;
}) {
  const t = useTranslations("stock");
  if (isError) return <p className="text-sm text-[var(--danger)]">{t("loadError")}</p>;
  if (isLoading) return <LoadingBlock />;
  return children;
}

export function formatQuantity(value: string): string {
  const number = Number(value);
  return Number.isInteger(number) ? String(number) : String(Number(number.toFixed(3)));
}

export function formatMoney(value: string): string {
  return `${Number(value).toFixed(2)} ₾`;
}
