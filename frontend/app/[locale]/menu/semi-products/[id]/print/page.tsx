"use client";

import { useParams, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { CrmAuthGate } from "@/components/crm/CrmAuthGate";
import { SemiProductPrint } from "@/components/menu/SemiProductPrint";
import { QueryState } from "@/components/menu/ui";
import { useCan } from "@/hooks/useAuth";
import { useSemiProducts } from "@/hooks/useStock";

function SemiProductPrintBody({ id, expanded }: { id: number; expanded: boolean }) {
  const t = useTranslations("stock");
  const crm = useTranslations("crm");
  const canViewMenu = useCan("view_menu");
  const semiProducts = useSemiProducts();
  const product = (semiProducts.list.data ?? []).find((row) => row.id === id) ?? null;

  if (!canViewMenu) {
    return <p className="py-16 text-center text-sm text-[var(--ink)]">{crm("adminOnly")}</p>;
  }

  if (!Number.isFinite(id) || id < 1) {
    return <p className="text-sm text-[var(--danger)]">{t("loadError")}</p>;
  }

  return (
    <QueryState isLoading={semiProducts.list.isLoading} isError={semiProducts.list.isError}>
      {product === null ? (
        <p className="text-sm text-[var(--danger)]">{t("loadError")}</p>
      ) : (
        <SemiProductPrint product={product} expanded={expanded} semiProducts={semiProducts.list.data ?? []} />
      )}
    </QueryState>
  );
}

export default function SemiProductPrintPage() {
  const params = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const id = Number(params.id);
  const expanded = searchParams.get("expanded") === "1";

  return (
    <div className="min-h-screen bg-white">
      <div className="mx-auto w-full max-w-[210mm] px-4 py-8 print:px-0 print:py-0">
        <CrmAuthGate>
          <SemiProductPrintBody id={id} expanded={expanded} />
        </CrmAuthGate>
      </div>
    </div>
  );
}
