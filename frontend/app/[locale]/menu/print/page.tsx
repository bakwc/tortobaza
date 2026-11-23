"use client";

import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { CrmAuthGate } from "@/components/crm/CrmAuthGate";
import { TechCardPrint } from "@/components/menu/TechCardPrint";
import { QueryState } from "@/components/menu/ui";
import { Button } from "@/components/ui/button";
import { useCan } from "@/hooks/useAuth";
import { useTechCardCategories, useTechCards } from "@/hooks/useStock";
import type { TechCard } from "@/lib/api/types";
import { cn } from "@/lib/utils";

function printIds(value: string | null): number[] {
  if (value === null || value === "") return [];
  const ids: number[] = [];
  for (const part of value.split(",")) {
    const id = Number(part);
    if (Number.isFinite(id) && id >= 1) ids.push(id);
  }
  return ids;
}

function selectedCards(cards: TechCard[], categories: { id: number }[], ids: number[]): TechCard[] {
  const picked = new Set(ids);
  const chosen = cards.filter((card) => picked.has(card.id));
  return [
    ...categories.flatMap((category) => chosen.filter((card) => card.category === category.id)),
    ...chosen.filter((card) => card.category === null),
  ];
}

function TechCardsPrintBody({ ids }: { ids: number[] }) {
  const t = useTranslations("stock");
  const crm = useTranslations("crm");
  const canViewMenu = useCan("view_menu");
  const techCards = useTechCards();
  const categories = useTechCardCategories();

  if (!canViewMenu) {
    return <p className="py-16 text-center text-sm text-[var(--ink)]">{crm("adminOnly")}</p>;
  }

  if (ids.length === 0) {
    return <p className="text-sm text-[var(--danger)]">{t("loadError")}</p>;
  }

  const cards = selectedCards(techCards.list.data ?? [], categories.list.data ?? [], ids);

  return (
    <QueryState
      isLoading={techCards.list.isLoading || categories.list.isLoading}
      isError={techCards.list.isError || categories.list.isError}
    >
      {cards.length === 0 ? (
        <p className="text-sm text-[var(--danger)]">{t("loadError")}</p>
      ) : (
        <div>
          <div className="mb-6 flex justify-end print:hidden">
            <Button type="button" onClick={() => window.print()}>
              {t("print")}
            </Button>
          </div>
          {cards.map((card, index) => (
            <div
              key={card.id}
              className={cn(index > 0 && "mt-10 print:mt-0", index < cards.length - 1 && "break-after-page")}
            >
              <TechCardPrint card={card} showPrintButton={false} expanded={false} techCards={[]} semiProducts={[]} />
            </div>
          ))}
        </div>
      )}
    </QueryState>
  );
}

export default function TechCardsPrintPage() {
  const searchParams = useSearchParams();
  const ids = printIds(searchParams.get("ids"));

  return (
    <div className="min-h-screen bg-white">
      <div className="mx-auto w-full max-w-[210mm] px-4 py-8 print:px-0 print:py-0">
        <CrmAuthGate>
          <TechCardsPrintBody ids={ids} />
        </CrmAuthGate>
      </div>
    </div>
  );
}
