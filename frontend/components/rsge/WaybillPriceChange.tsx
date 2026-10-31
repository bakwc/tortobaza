"use client";

import { ArrowRight, Minus, TrendingDown, TrendingUp } from "lucide-react";
import { useTranslations } from "next-intl";
import { formatUnitCost } from "@/components/menu/ui";
import { cn } from "@/lib/utils";

function decimalNumber(value: string): number {
  return Number(value.replace(",", "."));
}

function unitCostDraft(value: string): string {
  return value.replace(/(\.\d*?)0+$/, "$1").replace(/\.$/, "");
}

function priceLabel(pack: number, costQuantity: string, unitLabel: string): string {
  const trimmed = unitCostDraft(String(Math.round(pack * 1e6) / 1e6));
  return `${formatUnitCost(trimmed)} / ${unitCostDraft(costQuantity)} ${unitLabel}`;
}

export function WaybillPriceChange({
  avgCost,
  costQuantity,
  unitLabel,
  amount,
  quantity,
}: {
  avgCost: string | undefined;
  costQuantity: string;
  unitLabel: string;
  amount: string;
  quantity: string;
}) {
  const t = useTranslations("rsge");
  if (avgCost === undefined || quantity.trim() === "") return null;
  const quantityNumber = decimalNumber(quantity);
  const amountNumber = decimalNumber(amount);
  const costQuantityNumber = decimalNumber(costQuantity);
  const previous = decimalNumber(avgCost);
  if (
    !Number.isFinite(quantityNumber) ||
    quantityNumber <= 0 ||
    !Number.isFinite(amountNumber) ||
    !Number.isFinite(costQuantityNumber) ||
    !Number.isFinite(previous)
  ) {
    return null;
  }
  const nextPack = (amountNumber / quantityNumber) * costQuantityNumber;
  const nextText = priceLabel(nextPack, costQuantity, unitLabel);
  if (previous === 0) {
    return (
      <div className="flex flex-wrap items-center gap-3 rounded-2xl bg-[var(--brand)]/10 px-4 py-3">
        <div className="min-w-0 flex-1">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-[var(--brand)]">{t("priceWillBe")}</p>
          <p className="text-base font-semibold text-[var(--ink)]">{nextText}</p>
        </div>
        <span className="inline-flex shrink-0 items-center rounded-full bg-white/80 px-2.5 py-1 text-xs font-semibold text-[var(--brand)]">
          {t("priceNew")}
        </span>
      </div>
    );
  }
  const previousPack = previous * costQuantityNumber;
  const percent = ((nextPack - previousPack) / previousPack) * 100;
  const unchanged = Math.abs(percent) < 0.5;
  const up = percent > 0;
  const rounded = Math.round(percent);
  let Icon = TrendingDown;
  if (unchanged) Icon = Minus;
  else if (up) Icon = TrendingUp;
  return (
    <div
      className={cn(
        "flex flex-wrap items-center gap-3 rounded-2xl px-4 py-3",
        unchanged ? "bg-[var(--cream)]" : up ? "bg-[var(--danger)]/10" : "bg-emerald-50",
      )}
    >
      <div className="flex min-w-0 flex-1 items-center gap-3">
        <div className="min-w-0">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-[var(--muted-2)]">{t("priceWas")}</p>
          <p className="truncate text-sm text-[var(--muted-2)] line-through">{priceLabel(previousPack, costQuantity, unitLabel)}</p>
        </div>
        <ArrowRight className="h-4 w-4 shrink-0 text-[var(--muted-2)]" />
        <div className="min-w-0">
          <p
            className={cn(
              "text-[10px] font-semibold uppercase tracking-wide",
              unchanged ? "text-[var(--muted-2)]" : up ? "text-[var(--danger)]" : "text-emerald-700",
            )}
          >
            {t("priceWillBe")}
          </p>
          <p
            className={cn(
              "text-base font-semibold",
              unchanged ? "text-[var(--ink)]" : up ? "text-[var(--danger)]" : "text-emerald-700",
            )}
          >
            {nextText}
          </p>
        </div>
      </div>
      <span
        className={cn(
          "inline-flex shrink-0 items-center gap-1 rounded-full bg-white/80 px-2.5 py-1 text-xs font-semibold",
          unchanged ? "text-[var(--muted-2)]" : up ? "text-[var(--danger)]" : "text-emerald-700",
        )}
      >
        <Icon className="h-3.5 w-3.5" />
        {unchanged ? t("priceUnchanged") : `${rounded > 0 ? "+" : ""}${rounded}%`}
      </span>
    </div>
  );
}
