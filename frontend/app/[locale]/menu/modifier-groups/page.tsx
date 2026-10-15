"use client";

import { MenuShell } from "@/components/menu/MenuShell";
import { ModifierGroupsPanel } from "@/components/menu/ModifierGroupsPanel";

export default function MenuModifierGroupsPage() {
  return (
    <MenuShell section="modifier-groups">
      <ModifierGroupsPanel />
    </MenuShell>
  );
}
