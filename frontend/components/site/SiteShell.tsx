"use client";

import { Suspense, type ReactNode } from "react";
import { useTranslations } from "next-intl";

import { SectionShell } from "@/components/menu/SectionShell";
import { Spinner } from "@/components/ui/spinner";
import { useShowHidden } from "@/hooks/useSite";

export type SiteSection = "products" | "categories" | "landings" | "option-groups";

const TABS: { key: SiteSection; href: string; labelKey: "products" | "categories" | "landings" | "optionGroups" }[] =
  [
    { key: "products", href: "/site", labelKey: "products" },
    { key: "categories", href: "/site/categories", labelKey: "categories" },
    { key: "landings", href: "/site/landings", labelKey: "landings" },
    { key: "option-groups", href: "/site/option-groups", labelKey: "optionGroups" },
  ];

export function SiteShell({ section, children }: { section: SiteSection; children: ReactNode }) {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-[40vh] items-center justify-center">
          <Spinner className="h-6 w-6 text-[var(--brand)]" />
        </div>
      }
    >
      <SiteShellContent section={section}>{children}</SiteShellContent>
    </Suspense>
  );
}

function tabHref(href: string, showHidden: boolean): string {
  return showHidden ? `${href}?show_hidden=1` : href;
}

function SiteShellContent({ section, children }: { section: SiteSection; children: ReactNode }) {
  const t = useTranslations("site");
  const showHidden = useShowHidden();

  return (
    <SectionShell
      active={section}
      permission="view_catalog"
      tabs={TABS.map((tab) => ({
        key: tab.key,
        href: tabHref(tab.href, showHidden),
        label: t(tab.labelKey),
      }))}
    >
      {children}
    </SectionShell>
  );
}
