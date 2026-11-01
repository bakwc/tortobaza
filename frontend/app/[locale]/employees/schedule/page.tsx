"use client";

import { Suspense } from "react";
import { EmployeesShell } from "@/components/employees/EmployeesShell";
import { EmployeesMonthBar } from "@/components/employees/ScheduleGrid";
import { SchedulePanel } from "@/components/employees/SchedulePanel";
import { TimesheetPanel } from "@/components/employees/TimesheetPanel";
import { useCan } from "@/hooks/useAuth";

export default function EmployeesSchedulePage() {
  return (
    <EmployeesShell section="schedule">
      <Suspense>
        <EmployeesScheduleContent />
      </Suspense>
    </EmployeesShell>
  );
}

function EmployeesScheduleContent() {
  const canEditSchedule = useCan("edit_schedule");
  return (
    <div className="grid gap-6">
      <EmployeesMonthBar />
      <SchedulePanel />
      {canEditSchedule ? <TimesheetPanel /> : null}
    </div>
  );
}
