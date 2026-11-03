"use client";

import type { ReactNode } from "react";
import { useTranslations } from "next-intl";

import { SectionShell } from "@/components/menu/SectionShell";

export type SiteSection = "products" | "categories" | "landings" | "option-groups";

export function SiteShell({ section, children }: { section: SiteSection; children: ReactNode }) {
  const t = useTranslations("site");
  return (
    <SectionShell
      active={section}
      permission="view_catalog"
      tabs={[
        { key: "products", href: "/site", label: t("products") },
        { key: "categories", href: "/site/categories", label: t("categories") },
        { key: "landings", href: "/site/landings", label: t("landings") },
        { key: "option-groups", href: "/site/option-groups", label: t("optionGroups") },
      ]}
    >
      {children}
    </SectionShell>
  );
}
