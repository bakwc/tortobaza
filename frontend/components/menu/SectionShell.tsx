"use client";

import { Suspense, type ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { CrmAuthGate } from "@/components/crm/CrmAuthGate";
import { CrmOverflowMenu } from "@/components/crm/CrmOverflowMenu";
import { Link } from "@/i18n/navigation";

export type SectionTab = { key: string; href: string; label: string };

export function SectionShell({
  tabs,
  active,
  children,
}: {
  tabs: SectionTab[];
  active: string;
  children: ReactNode;
}) {
  return (
    <div className="mx-auto w-full max-w-5xl px-4 py-8 md:py-12">
      <CrmAuthGate>
        <div className="grid gap-6">
          <div className="flex items-start justify-between gap-2">
            <nav className="flex min-w-0 flex-1 flex-wrap gap-2">
              {tabs.map((tab) => (
                <Button key={tab.key} asChild variant={tab.key === active ? "primary" : "outline"}>
                  <Link href={tab.href}>{tab.label}</Link>
                </Button>
              ))}
            </nav>
            <div className="shrink-0">
              <Suspense>
                <CrmOverflowMenu />
              </Suspense>
            </div>
          </div>
          {children}
        </div>
      </CrmAuthGate>
    </div>
  );
}
