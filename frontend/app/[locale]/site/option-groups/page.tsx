"use client";

import { OptionGroupsPanel } from "@/components/site/OptionGroupsPanel";
import { SiteShell } from "@/components/site/SiteShell";

export default function SiteOptionGroupsPage() {
  return (
    <SiteShell section="option-groups">
      <OptionGroupsPanel />
    </SiteShell>
  );
}
