"use client";

import { Suspense, type ReactNode } from "react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { CrmAuthGate } from "@/components/crm/CrmAuthGate";
import { CrmOverflowMenu } from "@/components/crm/CrmOverflowMenu";
import { useCurrentUser } from "@/hooks/useAuth";
import { Link } from "@/i18n/navigation";

export type SectionTab = { key: string; href: string; label: string };

export function SectionShell({
  tabs,
  active,
  financeOnly,
  children,
}: {
  tabs: SectionTab[];
  active: string;
  financeOnly: boolean;
  children: ReactNode;
}) {
  const t = useTranslations("crm");
  const currentUser = useCurrentUser();
  const allowed = financeOnly
    ? Boolean(currentUser.data?.is_finance_admin)
    : Boolean(currentUser.data?.is_staff);

  return (
    <div className="mx-auto w-full max-w-5xl px-4 py-8 md:py-12">
      <CrmAuthGate>
        {allowed ? (
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
        ) : (
          <div className="grid gap-6">
            <div className="flex justify-end">
              <Suspense>
                <CrmOverflowMenu />
              </Suspense>
            </div>
            <div className="mx-auto max-w-md px-4 py-16 text-center text-sm text-[var(--ink)]">
              {financeOnly ? t("staffOnly") : t("adminOnly")}
            </div>
          </div>
        )}
      </CrmAuthGate>
    </div>
  );
}
