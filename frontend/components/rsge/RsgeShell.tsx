"use client";

import type { ReactNode } from "react";
import { useTranslations } from "next-intl";
import { SectionShell, type SectionTab } from "@/components/menu/SectionShell";

export type RsgeSection = "waybills";

export function RsgeShell({ section, children }: { section: RsgeSection; children: ReactNode }) {
  const t = useTranslations("rsge");
  const tabs: SectionTab[] = [{ key: "waybills", href: "/rsge", label: t("waybills") }];
  return (
    <SectionShell active={section} tabs={tabs}>
      {children}
    </SectionShell>
  );
}
