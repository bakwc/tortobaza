"use client";

import { Suspense, type ReactNode } from "react";
import { useTranslations } from "next-intl";
import { SectionShell, type SectionTab } from "@/components/menu/SectionShell";
import { Spinner } from "@/components/ui/spinner";
import { useCan } from "@/hooks/useAuth";
import { useFinancePeriod } from "@/hooks/useFinancePeriod";

export type EmployeesSection = "employees" | "groups" | "schedule" | "salaries";

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
  const canViewEmployees = useCan("view_employees");
  const canViewSchedule = useCan("view_schedule");
  const tabs: SectionTab[] = [
    ...(canViewEmployees
      ? [
          { key: "employees", href: "/employees", label: t("employeesSection") },
          { key: "groups", href: "/employees/groups", label: t("groupsSection") },
        ]
      : []),
    ...(canViewSchedule
      ? [{ key: "schedule", href: `/employees/schedule?${period.query}`, label: t("scheduleAndTimesheet") }]
      : []),
    ...(canViewEmployees
      ? [{ key: "salaries", href: `/employees/salaries?${period.query}`, label: t("salaries") }]
      : []),
  ];
  const permission = section === "schedule" ? "view_schedule" : "view_employees";
  return (
    <SectionShell active={section} permission={permission} tabs={tabs}>
      {children}
    </SectionShell>
  );
}
