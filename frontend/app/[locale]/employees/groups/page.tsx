"use client";

import { Suspense } from "react";
import { EmployeesShell } from "@/components/employees/EmployeesShell";
import { GroupsPanel } from "@/components/employees/GroupsPanel";

export default function EmployeeGroupsPage() {
  return (
    <EmployeesShell section="groups">
      <Suspense>
        <GroupsPanel />
      </Suspense>
    </EmployeesShell>
  );
}
