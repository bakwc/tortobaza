"use client";

import { useParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { CrmAuthGate } from "@/components/crm/CrmAuthGate";
import { CrmOrderForm } from "@/components/crm/CrmOrderForm";
import { Spinner } from "@/components/ui/spinner";
import { useCrmOrder } from "@/hooks/useCrmOrders";

function EditCrmOrderForm({ id }: { id: number }) {
  const t = useTranslations("crm");
  const orderQuery = useCrmOrder(id);

  if (!Number.isFinite(id) || id < 1) {
    return (
      <div className="rounded-3xl border border-[var(--line)] bg-white p-12 text-center text-sm text-[var(--danger)]">
        {t("loadOrderError")}
      </div>
    );
  }

  if (orderQuery.isLoading) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center">
        <Spinner className="h-6 w-6 text-[var(--brand)]" />
      </div>
    );
  }

  if (orderQuery.isError || !orderQuery.data) {
    return (
      <div className="rounded-3xl border border-[var(--line)] bg-white p-12 text-center text-sm text-[var(--danger)]">
        {t("loadOrderError")}
      </div>
    );
  }

  return <CrmOrderForm mode="edit" order={orderQuery.data} />;
}

export default function EditCrmOrderPage() {
  const params = useParams<{ id: string }>();
  const id = Number(params.id);

  return (
    <div className="mx-auto w-full max-w-3xl px-4 py-8 md:py-12">
      <CrmAuthGate>
        <EditCrmOrderForm id={id} />
      </CrmAuthGate>
    </div>
  );
}
