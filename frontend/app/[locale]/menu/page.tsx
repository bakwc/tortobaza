"use client";

import { Suspense } from "react";
import { MenuShell } from "@/components/menu/MenuShell";
import { TechCardsPanel } from "@/components/menu/TechCardsPanel";

export default function MenuTechCardsPage() {
  return (
    <MenuShell section="tech-cards">
      <Suspense>
        <TechCardsPanel />
      </Suspense>
    </MenuShell>
  );
}
