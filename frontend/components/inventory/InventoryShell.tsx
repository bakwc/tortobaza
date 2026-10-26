"use client";

import type { ReactNode } from "react";
import { useTranslations } from "next-intl";
import { SectionShell, type SectionTab } from "@/components/menu/SectionShell";
import { useCurrentUser } from "@/hooks/useAuth";

export type InventorySection =
  | "stock"
  | "supplies"
  | "suppliers"
  | "productions"
  | "finished"
  | "write-offs"
  | "inventory-counts";

const FINANCE_ADMIN_SECTIONS: string[] = ["supplies", "suppliers"];

export function InventoryShell({ section, children }: { section: InventorySection; children: ReactNode }) {
  const t = useTranslations("stock.inventory");
  const currentUser = useCurrentUser();
  const tabs: SectionTab[] = [
    { key: "stock", href: "/inventory", label: t("stock") },
    { key: "supplies", href: "/inventory/supplies", label: t("supplies") },
    { key: "suppliers", href: "/inventory/suppliers", label: t("suppliers") },
    { key: "productions", href: "/inventory/productions", label: t("productions") },
    { key: "finished", href: "/inventory/finished", label: t("finishedGoods") },
    { key: "write-offs", href: "/inventory/write-offs", label: t("writeOffs") },
    { key: "inventory-counts", href: "/inventory/inventory-counts", label: t("inventoryCounts") },
  ];
  const visibleTabs = currentUser.data?.is_finance_admin ? tabs : tabs.filter((tab) => !FINANCE_ADMIN_SECTIONS.includes(tab.key));
  return (
    <SectionShell active={section} financeOnly={false} tabs={visibleTabs}>
      {children}
    </SectionShell>
  );
}
