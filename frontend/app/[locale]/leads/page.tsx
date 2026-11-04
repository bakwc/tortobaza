import { Suspense } from "react";
import { LeadsMessagesPanel } from "@/components/leads/LeadsMessagesPanel";
import { Spinner } from "@/components/ui/spinner";

export default function LeadsMessagesPage() {
  return (
    <Suspense
      fallback={
        <div className="mx-auto flex min-h-[40vh] w-full max-w-5xl items-center justify-center px-4 py-8">
          <Spinner className="h-6 w-6 text-[var(--brand)]" />
        </div>
      }
    >
      <LeadsMessagesPanel section="messages" />
    </Suspense>
  );
}
