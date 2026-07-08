"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { AttendanceEventType, AttendanceSummary } from "@/lib/api/types";

export const attendanceSummaryQueryKey = ["attendance-summary"] as const;

export function useAttendanceSummary() {
  return useQuery<AttendanceSummary>({
    queryKey: attendanceSummaryQueryKey,
    queryFn: () => api.getAttendanceSummary(),
  });
}

export function useMarkAttendance() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (eventType: AttendanceEventType) => api.markAttendance(eventType),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: attendanceSummaryQueryKey });
    },
  });
}
