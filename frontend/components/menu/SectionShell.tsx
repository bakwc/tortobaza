"use client";

import { Suspense, type ReactNode } from "react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { CrmAuthGate } from "@/components/crm/CrmAuthGate";
import { CrmOverflowMenu } from "@/components/crm/CrmOverflowMenu";
import { useCan } from "@/hooks/useAuth";
import { Link } from "@/i18n/navigation";

export type SectionTab = { key: string; href: string; label: string };

export function SectionShell({
  tabs,
  active,
  permission,
  header,
  children,
}: {
  tabs: SectionTab[];
  active: string;
  permission: string;
  header?: ReactNode;
  children: ReactNode;
}) {
  const t = useTranslations("crm");
  const allowed = useCan(permission);

  return (
    <div className="mx-auto w-full max-w-5xl px-4 py-8 print:max-w-none print:p-0 md:py-12">
      <CrmAuthGate>
        {allowed ? (
          <div className="grid gap-6 print:gap-0">
            <div className="flex items-start justify-between gap-2 print:hidden">
              <nav className="flex min-w-0 flex-1 flex-wrap gap-2">
                {tabs.map((tab) => (
                  <Button key={tab.key} asChild variant={tab.key === active ? "primary" : "outline"}>
                    <Link href={tab.href}>{tab.label}</Link>
                  </Button>
                ))}
              </nav>
              {header ? <div className="shrink-0 self-center">{header}</div> : null}
              <div className="shrink-0">
                <Suspense>
                  <CrmOverflowMenu />
                </Suspense>
              </div>
            </div>
            {children}
          </div>
        ) : (
          <div className="grid gap-6">
            <div className="flex justify-end">
              <Suspense>
                <CrmOverflowMenu />
              </Suspense>
            </div>
            <div className="mx-auto max-w-md px-4 py-16 text-center text-sm text-[var(--ink)]">
              {t("adminOnly")}
            </div>
          </div>
        )}
      </CrmAuthGate>
    </div>
  );
}
