import { InvoicesPanel } from "@/components/rsge/InvoicesPanel";
import { RsgeShell } from "@/components/rsge/RsgeShell";

export default function RsgeInvoicesPage() {
  return (
    <RsgeShell section="invoices">
      <InvoicesPanel />
    </RsgeShell>
  );
}
