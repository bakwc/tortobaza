"use client";

import { Languages } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";

export type SiteLocale = "en" | "ka" | "ru";

export const SITE_LOCALES: SiteLocale[] = ["en", "ka", "ru"];

function textOf(row: object, key: string): string {
  const value = (row as Record<string, unknown>)[key];
  return typeof value === "string" ? value : "";
}

export function hasAnyValue(row: object, field: string): boolean {
  return SITE_LOCALES.some((code) => textOf(row, `${field}_${code}`).trim() !== "");
}

export function filledFields(
  row: object,
  locale: SiteLocale,
  fields: readonly string[],
): Record<string, string> {
  const result: Record<string, string> = {};
  for (const field of fields) {
    const value = textOf(row, `${field}_${locale}`);
    if (value.trim() !== "") result[field] = value;
  }
  return result;
}

export function applyTranslatedFields(
  fields: Record<string, Record<SiteLocale, string>>,
  source: SiteLocale,
): Record<string, string> {
  const patch: Record<string, string> = {};
  for (const [field, values] of Object.entries(fields)) {
    for (const code of SITE_LOCALES) {
      if (code !== source) patch[`${field}_${code}`] = values[code];
    }
  }
  return patch;
}

export function TranslateFieldsButton({
  label,
  pending,
  disabled,
  onClick,
}: {
  label: string;
  pending: boolean;
  disabled: boolean;
  onClick: () => void;
}) {
  return (
    <Button type="button" size="sm" variant="outline" disabled={disabled || pending} onClick={onClick}>
      {pending ? <Spinner className="mr-1 h-4 w-4" /> : <Languages className="mr-1 h-4 w-4" />}
      {label}
    </Button>
  );
}

export function LocaleTabs({
  locale,
  onChange,
  labels,
}: {
  locale: SiteLocale;
  onChange: (value: SiteLocale) => void;
  labels: Record<SiteLocale, string>;
}) {
  return (
    <div className="flex flex-wrap gap-2">
      {SITE_LOCALES.map((value) => (
        <Button
          key={value}
          type="button"
          size="sm"
          variant={locale === value ? "primary" : "outline"}
          onClick={() => onChange(value)}
        >
          {labels[value]}
        </Button>
      ))}
    </div>
  );
}
