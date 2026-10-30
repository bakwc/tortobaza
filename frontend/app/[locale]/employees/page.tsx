"use client";

import { Suspense } from "react";
import { EmployeesPanel } from "@/components/employees/EmployeesPanel";
import { EmployeesShell } from "@/components/employees/EmployeesShell";

export default function EmployeesPage() {
  return (
    <EmployeesShell section="employees">
      <Suspense>
        <EmployeesPanel />
      </Suspense>
    </EmployeesShell>
  );
}
