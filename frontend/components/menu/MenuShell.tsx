"use client";

import type { ReactNode } from "react";
import { useTranslations } from "next-intl";
import { SectionShell } from "@/components/menu/SectionShell";

export type MenuSection = "tech-cards" | "ingredients" | "semi-products" | "modifier-groups";

export function MenuShell({ section, children }: { section: MenuSection; children: ReactNode }) {
  const t = useTranslations("stock.menu");
  return (
    <SectionShell
      active={section}
      financeOnly={false}
      tabs={[
        { key: "tech-cards", href: "/menu", label: t("techCards") },
        { key: "ingredients", href: "/menu/ingredients", label: t("ingredients") },
        { key: "semi-products", href: "/menu/semi-products", label: t("semiProducts") },
        { key: "modifier-groups", href: "/menu/modifier-groups", label: t("modifierGroups") },
      ]}
    >
      {children}
    </SectionShell>
  );
}
