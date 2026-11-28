"use client";

import type { ReactNode } from "react";
import { useTranslations } from "next-intl";
import { SectionShell, type SectionTab } from "@/components/menu/SectionShell";

export type WishlistSection = "purchases" | "ideas" | "tasks";

export function WishlistShell({ section, children }: { section: WishlistSection; children: ReactNode }) {
  const t = useTranslations("wishlist");
  const tabs: SectionTab[] = [
    { key: "tasks", href: "/wishlist", label: t("tasks") },
    { key: "purchases", href: "/wishlist/purchases", label: t("purchases") },
    { key: "ideas", href: "/wishlist/ideas", label: t("ideas") },
  ];
  return (
    <SectionShell active={section} permission="view_wishlist" tabs={tabs}>
      {children}
    </SectionShell>
  );
}
