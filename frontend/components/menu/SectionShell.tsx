"use client";

import { Suspense, type ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { CrmAuthGate } from "@/components/crm/CrmAuthGate";
import { CrmOverflowMenu } from "@/components/crm/CrmOverflowMenu";
import { Link } from "@/i18n/navigation";

export type SectionTab = { key: string; href: string; label: string };

export function SectionShell({
  title,
  tabs,
  active,
  children,
}: {
  title: string;
  tabs: SectionTab[];
  active: string;
  children: ReactNode;
}) {
  return (
    <div className="mx-auto w-full max-w-5xl px-4 py-8 md:py-12">
      <CrmAuthGate>
        <div className="grid gap-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h1 className="text-2xl font-semibold text-[var(--ink)]">{title}</h1>
            <Suspense>
              <CrmOverflowMenu />
            </Suspense>
          </div>
          <nav className="flex flex-wrap gap-2">
            {tabs.map((tab) => (
              <Button key={tab.key} asChild variant={tab.key === active ? "primary" : "outline"}>
                <Link href={tab.href}>{tab.label}</Link>
              </Button>
            ))}
          </nav>
          {children}
        </div>
      </CrmAuthGate>
    </div>
  );
}
