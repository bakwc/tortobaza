"use client";

import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Link } from "@/i18n/navigation";
import { useCrmUnconfirmedOrders } from "@/hooks/useCrmOrders";
import { cn } from "@/lib/utils";

export function CrmUnconfirmedOrdersLink() {
  const t = useTranslations("crm");
  const ordersQuery = useCrmUnconfirmedOrders();
  const count = ordersQuery.data?.orders.length ?? 0;
  const hasUnconfirmed = count > 0;

  return (
    <Button
      asChild
      variant="outline"
      className={cn(
        hasUnconfirmed &&
          "border-red-600 bg-red-600 text-white hover:bg-red-700 hover:text-white",
      )}
    >
      <Link href="/crm/unconfirmed">
        {t("unconfirmedOrders")}
        <span
          className={cn(
            "ml-2 inline-flex min-w-5 items-center justify-center rounded-full px-1.5 text-xs font-bold",
            hasUnconfirmed
              ? "animate-pulse bg-white text-red-600"
              : "bg-[var(--cream)] text-[var(--ink)]",
          )}
        >
          {count}
        </span>
      </Link>
    </Button>
  );
}
