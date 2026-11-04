"use client";

import type { ReactNode } from "react";
import { useTranslations } from "next-intl";
import { SectionShell, type SectionTab } from "@/components/menu/SectionShell";

export type LeadsSection = "messages" | "potential" | "channels" | "keywords";

export function LeadsShell({ section, children }: { section: LeadsSection; children: ReactNode }) {
  const t = useTranslations("leads");
  const tabs: SectionTab[] = [
    { key: "messages", href: "/leads", label: t("messages") },
    { key: "potential", href: "/leads/potential", label: t("potential") },
    { key: "channels", href: "/leads/channels", label: t("channels") },
    { key: "keywords", href: "/leads/keywords", label: t("keywords") },
  ];
  return (
    <SectionShell active={section} permission="view_leads" tabs={tabs}>
      {children}
    </SectionShell>
  );
}
