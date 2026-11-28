"use client";

import type { ReactNode } from "react";
import { useTranslations } from "next-intl";
import { SectionShell, type SectionTab } from "@/components/menu/SectionShell";

export type WishlistSection = "purchases" | "ideas" | "tasks";

export function WishlistShell({ section, children }: { section: WishlistSection; children: ReactNode }) {
  const t = useTranslations("wishlist");
  const tabs: SectionTab[] = [
    { key: "purchases", href: "/wishlist", label: t("purchases") },
    { key: "ideas", href: "/wishlist/ideas", label: t("ideas") },
    { key: "tasks", href: "/wishlist/tasks", label: t("tasks") },
  ];
  return (
    <SectionShell active={section} permission="view_wishlist" tabs={tabs}>
      {children}
    </SectionShell>
  );
}
