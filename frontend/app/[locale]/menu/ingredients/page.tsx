"use client";

import { IngredientsPanel } from "@/components/menu/IngredientsPanel";
import { MenuShell } from "@/components/menu/MenuShell";

export default function MenuIngredientsPage() {
  return (
    <MenuShell section="ingredients">
      <IngredientsPanel />
    </MenuShell>
  );
}
