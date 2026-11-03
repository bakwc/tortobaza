"use client";

import { Button } from "@/components/ui/button";

export type SiteLocale = "en" | "ka" | "ru";

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
