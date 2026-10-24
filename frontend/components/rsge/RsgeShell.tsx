"use client";

import type { ReactNode } from "react";
import { useTranslations } from "next-intl";
import { SectionShell, type SectionTab } from "@/components/menu/SectionShell";

export type RsgeSection = "waybills" | "invoices";

export function RsgeShell({ section, children }: { section: RsgeSection; children: ReactNode }) {
  const t = useTranslations("rsge");
  const tabs: SectionTab[] = [
    { key: "waybills", href: "/rsge", label: t("waybills") },
    { key: "invoices", href: "/rsge/invoices", label: t("invoices") },
  ];
  return (
    <SectionShell active={section} tabs={tabs}>
      {children}
    </SectionShell>
  );
}
