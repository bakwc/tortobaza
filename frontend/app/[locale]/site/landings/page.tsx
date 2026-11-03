"use client";

import { LandingsPanel } from "@/components/site/LandingsPanel";
import { SiteShell } from "@/components/site/SiteShell";

export default function SiteLandingsPage() {
  return (
    <SiteShell section="landings">
      <LandingsPanel />
    </SiteShell>
  );
}
