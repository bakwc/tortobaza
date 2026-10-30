"use client";

import { AnalyticsShell } from "@/components/analytics/AnalyticsShell";
import { EmployeesPanel } from "@/components/analytics/EmployeesPanel";

export default function AnalyticsEmployeesPage() {
  return (
    <AnalyticsShell section="employees">
      <EmployeesPanel />
    </AnalyticsShell>
  );
}
