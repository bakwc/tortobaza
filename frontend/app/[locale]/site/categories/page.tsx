"use client";

import { CategoriesPanel } from "@/components/site/CategoriesPanel";
import { SiteShell } from "@/components/site/SiteShell";

export default function SiteCategoriesPage() {
  return (
    <SiteShell section="categories">
      <CategoriesPanel />
    </SiteShell>
  );
}
