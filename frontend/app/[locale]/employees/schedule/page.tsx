"use client";

import { Suspense } from "react";
import { EmployeesShell } from "@/components/employees/EmployeesShell";
import { EmployeesMonthBar } from "@/components/employees/ScheduleGrid";
import { SchedulePanel } from "@/components/employees/SchedulePanel";
import { TimesheetPanel } from "@/components/employees/TimesheetPanel";

export default function EmployeesSchedulePage() {
  return (
    <EmployeesShell section="schedule">
      <Suspense>
        <div className="grid gap-6">
          <EmployeesMonthBar />
          <SchedulePanel />
          <TimesheetPanel />
        </div>
      </Suspense>
    </EmployeesShell>
  );
}
