"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { Package } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { CrmAuthGate } from "@/components/crm/CrmAuthGate";
import { CrmOrdersMap } from "@/components/crm/CrmOrdersMap";
import { CrmOverflowMenu } from "@/components/crm/CrmOverflowMenu";
import { Link, useRouter } from "@/i18n/navigation";
import { useCrmMapOrders } from "@/hooks/useCrmOrders";
import type { CrmMapOrderRange } from "@/lib/api/types";

function parseRange(value: string | null): CrmMapOrderRange {
  if (value === "today") {
    return "today";
  }
  return "next_3_hours";
}

export default function CrmMapPage() {
  return (
    <div className="flex h-[100dvh] min-h-0 flex-col overflow-hidden px-3 py-3 md:px-4 md:py-4">
      <CrmAuthGate>
        <Suspense
          fallback={
            <div className="flex min-h-0 flex-1 items-center justify-center">
              <Spinner className="h-6 w-6 text-[var(--brand)]" />
            </div>
          }
        >
          <CrmMapBoard />
        </Suspense>
      </CrmAuthGate>
    </div>
  );
}

function CrmMapBoard() {
  const t = useTranslations("crm");
  const router = useRouter();
  const searchParams = useSearchParams();
  const range = parseRange(searchParams.get("range"));
  const ordersQuery = useCrmMapOrders(range);
  const orders = ordersQuery.data?.orders ?? [];

  const setRange = (next: CrmMapOrderRange) => {
    router.replace(`/crm/map?range=${next}`);
  };

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap gap-2">
          <Button
            size="sm"
            variant={range === "next_3_hours" ? "primary" : "outline"}
            onClick={() => setRange("next_3_hours")}
          >
            {t("mapNext3Hours")}
          </Button>
          <Button
            size="sm"
            variant={range === "today" ? "primary" : "outline"}
            onClick={() => setRange("today")}
          >
            {t("today")}
          </Button>
        </div>
        <div className="flex flex-wrap justify-end gap-2">
          <Button asChild variant="outline">
            <Link href="/crm">{t("dailyBoard")}</Link>
          </Button>
          <Button asChild variant="outline">
            <Link href="/crm/month">{t("monthlyOrders")}</Link>
          </Button>
          <CrmOverflowMenu />
        </div>
      </div>
      <div className="relative min-h-0 flex-1 overflow-hidden rounded-3xl border border-[var(--line)] bg-white shadow-sm">
        {ordersQuery.isLoading ? (
          <div className="flex h-full items-center justify-center">
            <Spinner className="h-8 w-8 text-[var(--brand)]" />
          </div>
        ) : ordersQuery.isError ? (
          <div className="flex h-full items-center justify-center p-8 text-center text-sm text-[var(--danger)]">
            {t("mapLoadError")}
          </div>
        ) : (
          <>
            <CrmOrdersMap orders={orders} />
            {orders.length === 0 ? (
              <div className="pointer-events-none absolute inset-x-0 top-4 z-10 flex justify-center px-4">
                <div className="pointer-events-auto flex max-w-md items-start gap-3 rounded-2xl border border-[var(--line)] bg-white/95 px-4 py-3 shadow-md">
                  <Package className="mt-0.5 h-5 w-5 shrink-0 text-[var(--muted)]" />
                  <div>
                    <p className="text-sm font-semibold text-[var(--ink)]">
                      {t("mapEmptyTitle")}
                    </p>
                    <p className="text-xs text-[var(--muted-2)]">{t("mapEmptyHint")}</p>
                  </div>
                </div>
              </div>
            ) : null}
          </>
        )}
      </div>
    </div>
  );
}
