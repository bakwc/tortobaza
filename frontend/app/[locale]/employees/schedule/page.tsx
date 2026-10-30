"use client";

import { Suspense } from "react";
import { EmployeesShell } from "@/components/employees/EmployeesShell";
import { SchedulePanel } from "@/components/employees/SchedulePanel";

export default function EmployeesSchedulePage() {
  return (
    <EmployeesShell section="schedule">
      <Suspense>
        <SchedulePanel />
      </Suspense>
    </EmployeesShell>
  );
}
