"use client";

import { useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { AttendanceEventType } from "@/lib/api/types";

export function useMarkAttendance() {
  return useMutation({
    mutationFn: (eventType: AttendanceEventType) => api.markAttendance(eventType),
  });
}
