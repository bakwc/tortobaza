"use client";

import { Suspense } from "react";
import { EmployeesShell } from "@/components/employees/EmployeesShell";
import { TimesheetPanel } from "@/components/employees/TimesheetPanel";

export default function EmployeesTimesheetPage() {
  return (
    <EmployeesShell section="timesheet">
      <Suspense>
        <TimesheetPanel />
      </Suspense>
    </EmployeesShell>
  );
}
