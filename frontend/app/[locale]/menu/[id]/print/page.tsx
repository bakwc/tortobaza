"use client";

import { useQuery } from "@tanstack/react-query";
import { useParams, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { CrmAuthGate } from "@/components/crm/CrmAuthGate";
import { TechCardPrint } from "@/components/menu/TechCardPrint";
import { QueryState } from "@/components/menu/ui";
import { useCan } from "@/hooks/useAuth";
import { useTechCards } from "@/hooks/useStock";
import { api } from "@/lib/api";

function TechCardPrintBody({ id, expanded }: { id: number; expanded: boolean }) {
  const t = useTranslations("stock");
  const crm = useTranslations("crm");
  const canViewMenu = useCan("view_menu");
  const techCards = useTechCards();
  const semiProducts = useQuery({
    queryKey: ["menu", "semi-products"],
    queryFn: () => api.menuSemiProducts.list(),
    enabled: expanded,
  });
  const card = (techCards.list.data ?? []).find((row) => row.id === id) ?? null;

  if (!canViewMenu) {
    return <p className="py-16 text-center text-sm text-[var(--ink)]">{crm("adminOnly")}</p>;
  }

  if (!Number.isFinite(id) || id < 1) {
    return <p className="text-sm text-[var(--danger)]">{t("loadError")}</p>;
  }

  return (
    <QueryState
      isLoading={techCards.list.isLoading || (expanded && semiProducts.data === undefined)}
      isError={techCards.list.isError || (expanded && semiProducts.isError)}
    >
      {card === null ? (
        <p className="text-sm text-[var(--danger)]">{t("loadError")}</p>
      ) : (
        <TechCardPrint
          card={card}
          showPrintButton
          expanded={expanded}
          techCards={techCards.list.data ?? []}
          semiProducts={semiProducts.data ?? []}
        />
      )}
    </QueryState>
  );
}

export default function TechCardPrintPage() {
  const params = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const id = Number(params.id);
  const expanded = searchParams.get("expanded") === "1";

  return (
    <div className="min-h-screen bg-white">
      <div className="mx-auto w-full max-w-[210mm] px-4 py-8 print:px-0 print:py-0">
        <CrmAuthGate>
          <TechCardPrintBody id={id} expanded={expanded} />
        </CrmAuthGate>
      </div>
    </div>
  );
}
