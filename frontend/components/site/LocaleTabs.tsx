"use client";

import { Button } from "@/components/ui/button";

export type SiteLocale = "en" | "ka" | "ru";

export function hasAnyName(row: Record<`name_${SiteLocale}`, string>): boolean {
  return (["en", "ka", "ru"] as SiteLocale[]).some((code) => row[`name_${code}`].trim() !== "");
}

export function otherLocaleNames(
  names: Record<SiteLocale, string>,
  source: SiteLocale,
): Partial<Record<`name_${SiteLocale}`, string>> {
  return Object.fromEntries(
    (["en", "ka", "ru"] as SiteLocale[])
      .filter((code) => code !== source)
      .map((code) => [`name_${code}`, names[code]]),
  ) as Partial<Record<`name_${SiteLocale}`, string>>;
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
      {(["en", "ka", "ru"] as SiteLocale[]).map((value) => (
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
