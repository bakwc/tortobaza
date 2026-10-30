"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { ScheduleCellBody, ScheduleFillBody, ScheduleGrid, TimesheetGrid } from "@/lib/api/types";

export function scheduleQueryKey(month: string) {
  return ["schedule", month] as const;
}

export function timesheetQueryKey(month: string) {
  return ["timesheet", month] as const;
}

function useInvalidateSchedule(month: string) {
  const qc = useQueryClient();
  return () => {
    qc.invalidateQueries({ queryKey: scheduleQueryKey(month) });
    qc.invalidateQueries({ queryKey: timesheetQueryKey(month) });
  };
}

export function useSchedule(month: string) {
  return useQuery<ScheduleGrid>({
    queryKey: scheduleQueryKey(month),
    queryFn: () => api.getSchedule(month),
  });
}

export function useTimesheet(month: string) {
  return useQuery<TimesheetGrid>({
    queryKey: timesheetQueryKey(month),
    queryFn: () => api.getTimesheet(month),
  });
}

export function useSaveSchedule(month: string) {
  const qc = useQueryClient();
  const invalidate = useInvalidateSchedule(month);
  return useMutation({
    mutationFn: (cells: ScheduleCellBody[]) => api.saveSchedule(cells),
    onMutate: (cells) => {
      qc.setQueryData<ScheduleGrid>(scheduleQueryKey(month), (current) => {
        if (!current) return current;
        return {
          ...current,
          employees: current.employees.map((employee) => applyCells(employee, cells)),
        };
      });
    },
    onSettled: invalidate,
  });
}

function applyCells(
  employee: ScheduleGrid["employees"][number],
  cells: ScheduleCellBody[],
): ScheduleGrid["employees"][number] {
  const days = { ...employee.days };
  for (const cell of cells) {
    if (cell.user !== employee.id) continue;
    if (cell.day_type === null) {
      delete days[cell.date];
      continue;
    }
    days[cell.date] = cell.day_type;
  }
  return { ...employee, days };
}

export function useFillSchedule(month: string) {
  const invalidate = useInvalidateSchedule(month);
  return useMutation({
    mutationFn: (body: ScheduleFillBody) => api.fillSchedule(body),
    onSuccess: invalidate,
  });
}
