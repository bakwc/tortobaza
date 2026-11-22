"use client";

import { OptionsPanel } from "@/components/site/OptionsPanel";
import { SiteShell } from "@/components/site/SiteShell";

export default function SiteOptionsPage() {
  return (
    <SiteShell section="options">
      <OptionsPanel />
    </SiteShell>
  );
}
