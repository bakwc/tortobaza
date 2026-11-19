"use client";

import type { ReactNode } from "react";
import { useTranslations } from "next-intl";
import { SectionShell, type SectionTab } from "@/components/menu/SectionShell";

export function WishlistShell({ children }: { children: ReactNode }) {
  const t = useTranslations("wishlist");
  const tabs: SectionTab[] = [{ key: "wishlist", href: "/wishlist", label: t("title") }];
  return (
    <SectionShell active="wishlist" permission="view_wishlist" tabs={tabs}>
      {children}
    </SectionShell>
  );
}
