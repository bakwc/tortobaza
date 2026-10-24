"use client";

import { AnalyticsShell } from "@/components/analytics/AnalyticsShell";
import { LoadPanel } from "@/components/analytics/LoadPanel";

export default function AnalyticsLoadPage() {
  return (
    <AnalyticsShell section="load">
      <LoadPanel />
    </AnalyticsShell>
  );
}
