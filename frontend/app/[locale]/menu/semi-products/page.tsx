"use client";

import { MenuShell } from "@/components/menu/MenuShell";
import { SemiProductsPanel } from "@/components/menu/SemiProductsPanel";

export default function MenuSemiProductsPage() {
  return (
    <MenuShell section="semi-products">
      <SemiProductsPanel />
    </MenuShell>
  );
}
