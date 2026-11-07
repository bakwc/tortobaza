"use client";

import type { ReactNode } from "react";
import { useTranslations } from "next-intl";
import { SectionShell, type SectionTab } from "@/components/menu/SectionShell";

export type LeadsSection = "messages" | "channels" | "keywords" | "verticals";

export function LeadsShell({ section, children }: { section: LeadsSection; children: ReactNode }) {
  const t = useTranslations("leads");
  const tabs: SectionTab[] = [
    { key: "messages", href: "/leads", label: t("messages") },
    { key: "channels", href: "/leads/channels", label: t("channels") },
    { key: "keywords", href: "/leads/keywords", label: t("keywords") },
    { key: "verticals", href: "/leads/verticals", label: t("verticals") },
  ];
  return (
    <SectionShell active={section} permission="view_leads" tabs={tabs}>
      {children}
    </SectionShell>
  );
}
