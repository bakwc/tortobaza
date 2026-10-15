"use client";

import { InventoryShell } from "@/components/inventory/InventoryShell";
import { WriteOffsPanel } from "@/components/inventory/WriteOffsPanel";

export default function InventoryWriteOffsPage() {
  return (
    <InventoryShell section="write-offs">
      <WriteOffsPanel />
    </InventoryShell>
  );
}
