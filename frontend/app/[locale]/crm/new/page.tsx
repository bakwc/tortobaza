"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { CrmAuthGate } from "@/components/crm/CrmAuthGate";
import { CrmOrderForm } from "@/components/crm/CrmOrderForm";
import { Spinner } from "@/components/ui/spinner";
import { getTbilisiTodayIsoDate } from "@/lib/format";

function NewCrmOrderForm() {
  const searchParams = useSearchParams();
  const dateParam = searchParams.get("date");
  const initialDate = dateParam ?? getTbilisiTodayIsoDate();
  return <CrmOrderForm mode="create" initialDate={initialDate} />;
}

export default function NewCrmOrderPage() {
  return (
    <div className="mx-auto w-full max-w-3xl px-4 py-8 md:py-12">
      <CrmAuthGate>
        <Suspense
          fallback={
            <div className="flex min-h-[40vh] items-center justify-center">
              <Spinner className="h-6 w-6 text-[var(--brand)]" />
            </div>
          }
        >
          <NewCrmOrderForm />
        </Suspense>
      </CrmAuthGate>
    </div>
  );
}
