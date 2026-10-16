"use client";

import { useParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { CrmAuthGate } from "@/components/crm/CrmAuthGate";
import { TechCardPrint } from "@/components/menu/TechCardPrint";
import { QueryState } from "@/components/menu/ui";
import { useCurrentUser } from "@/hooks/useAuth";
import { useTechCards } from "@/hooks/useStock";

function TechCardPrintBody({ id }: { id: number }) {
  const t = useTranslations("stock");
  const crm = useTranslations("crm");
  const currentUser = useCurrentUser();
  const techCards = useTechCards();
  const card = (techCards.list.data ?? []).find((row) => row.id === id) ?? null;

  if (!currentUser.data?.is_staff) {
    return <p className="py-16 text-center text-sm text-[var(--ink)]">{crm("adminOnly")}</p>;
  }

  if (!Number.isFinite(id) || id < 1) {
    return <p className="text-sm text-[var(--danger)]">{t("loadError")}</p>;
  }

  return (
    <QueryState isLoading={techCards.list.isLoading} isError={techCards.list.isError}>
      {card === null ? <p className="text-sm text-[var(--danger)]">{t("loadError")}</p> : <TechCardPrint card={card} />}
    </QueryState>
  );
}

export default function TechCardPrintPage() {
  const params = useParams<{ id: string }>();
  const id = Number(params.id);

  return (
    <div className="min-h-screen bg-white">
      <div className="mx-auto w-full max-w-[210mm] px-4 py-8 print:px-0 print:py-0">
        <CrmAuthGate>
          <TechCardPrintBody id={id} />
        </CrmAuthGate>
      </div>
    </div>
  );
}
