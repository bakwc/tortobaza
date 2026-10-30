"use client";

import { Suspense, type ReactNode } from "react";
import { useTranslations } from "next-intl";
import { SectionShell, type SectionTab } from "@/components/menu/SectionShell";
import { Spinner } from "@/components/ui/spinner";
import { useFinancePeriod } from "@/hooks/useFinancePeriod";

export type EmployeesSection = "employees" | "salaries";

export function EmployeesShell({ section, children }: { section: EmployeesSection; children: ReactNode }) {
  return (
    <Suspense
      fallback={
        <div className="mx-auto flex min-h-[40vh] w-full max-w-5xl items-center justify-center px-4 py-8">
          <Spinner className="h-6 w-6 text-[var(--brand)]" />
        </div>
      }
    >
      <EmployeesShellContent section={section}>{children}</EmployeesShellContent>
    </Suspense>
  );
}

function EmployeesShellContent({ section, children }: { section: EmployeesSection; children: ReactNode }) {
  const t = useTranslations("crm");
  const period = useFinancePeriod();
  const tabs: SectionTab[] = [
    { key: "employees", href: "/employees", label: t("employeesSection") },
    { key: "salaries", href: `/employees/salaries?${period.query}`, label: t("salaries") },
  ];
  return (
    <SectionShell active={section} financeOnly tabs={tabs}>
      {children}
    </SectionShell>
  );
}
