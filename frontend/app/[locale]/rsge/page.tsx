import { RsgeShell } from "@/components/rsge/RsgeShell";
import { WaybillsPanel } from "@/components/rsge/WaybillsPanel";

export default function RsgeWaybillsPage() {
  return (
    <RsgeShell section="waybills">
      <WaybillsPanel />
    </RsgeShell>
  );
}
