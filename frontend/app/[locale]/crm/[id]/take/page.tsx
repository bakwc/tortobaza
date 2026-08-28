"use client";

import { useEffect } from "react";
import { useParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { CrmAuthGate } from "@/components/crm/CrmAuthGate";
import { Spinner } from "@/components/ui/spinner";
import { usePatchCrmOrder } from "@/hooks/useCrmOrders";
import { useRouter } from "@/i18n/navigation";

function TakeCrmOrder({ id }: { id: number }) {
  const t = useTranslations("crm");
  const router = useRouter();
  const patchMutation = usePatchCrmOrder();
  const mutate = patchMutation.mutate;

  useEffect(() => {
    if (!Number.isFinite(id) || id < 1) {
      return;
    }
    mutate(
      { id, body: { take_in_work: true } },
      {
        onSuccess: (order) => {
          router.replace(`/crm?date=${order.date}&order=${order.id}`);
        },
      },
    );
  }, [id, mutate, router]);

  if (!Number.isFinite(id) || id < 1 || patchMutation.isError) {
    return (
      <div className="rounded-3xl border border-[var(--line)] bg-white p-12 text-center text-sm text-[var(--danger)]">
        {t("loadOrderError")}
      </div>
    );
  }

  return (
    <div className="flex min-h-[40vh] items-center justify-center">
      <Spinner className="h-6 w-6 text-[var(--brand)]" />
    </div>
  );
}

export default function TakeCrmOrderPage() {
  const params = useParams<{ id: string }>();
  const id = Number(params.id);

  return (
    <div className="mx-auto w-full max-w-3xl px-4 py-8 md:py-12">
      <CrmAuthGate>
        <TakeCrmOrder id={id} />
      </CrmAuthGate>
    </div>
  );
}
