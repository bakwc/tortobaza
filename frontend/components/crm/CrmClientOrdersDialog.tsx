"use client";

import { Cake } from "lucide-react";
import { useTranslations } from "next-intl";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { Spinner } from "@/components/ui/spinner";
import { Link } from "@/i18n/navigation";
import { useCrmClientOrders } from "@/hooks/useCrmOrders";
import type { CrmClientOrderHistory } from "@/lib/api/types";
import { CRM_ORDER_STATUS_MESSAGE_KEYS, crmOrderStatusTone } from "@/lib/crmStatus";
import { formatAmount } from "@/lib/format";
import { cn } from "@/lib/utils";

function formatOrderDate(iso: string): string {
  const [year, month, day] = iso.split("-");
  return `${day}.${month}.${year}`;
}

function orderSummary(order: CrmClientOrderHistory): string {
  if (!order.filling) {
    return order.weight;
  }
  return `${order.weight} · ${order.filling}`;
}

function ClientOrderRow({
  order,
  current,
  onOpen,
}: {
  order: CrmClientOrderHistory;
  current: boolean;
  onOpen: () => void;
}) {
  const t = useTranslations("crm");
  const tone = crmOrderStatusTone(order.status);
  const className = cn(
    "flex h-14 items-center gap-3 overflow-hidden px-4",
    current ? "bg-[var(--brand)]/10" : "hover:bg-[var(--cream-soft)]",
  );
  const body = (
    <>
      <span className="flex h-10 w-10 shrink-0 items-center justify-center overflow-hidden rounded-lg bg-[var(--cream)]">
        {order.image ? (
          <img
            src={order.image.src}
            srcSet={order.image.srcset}
            sizes="40px"
            alt=""
            className="h-full w-full object-cover"
          />
        ) : (
          <Cake className="h-4 w-4 text-[var(--ink)]/40" />
        )}
      </span>
      <span className="min-w-0 flex-1">
        <span className="block truncate text-sm font-medium leading-5 text-[var(--ink)]">
          {formatOrderDate(order.date)} · #{order.id}
        </span>
        <span className="block truncate text-xs leading-4 text-[var(--ink)]/60">{orderSummary(order)}</span>
      </span>
      <span className="flex shrink-0 flex-col items-end gap-1">
        <span className="text-sm font-semibold leading-none text-[var(--ink)]">
          {formatAmount(order.total)} ₾
        </span>
        <span
          className={cn(
            "whitespace-nowrap rounded-full px-2 py-0.5 text-[10px] font-semibold leading-none",
            tone.chip,
          )}
        >
          {t(CRM_ORDER_STATUS_MESSAGE_KEYS[order.status])}
        </span>
      </span>
    </>
  );
  if (current) {
    return <div className={className}>{body}</div>;
  }
  return (
    <Link href={`/crm?date=${order.date}&order=${order.id}`} onClick={onOpen} className={className}>
      {body}
    </Link>
  );
}

export function CrmClientOrdersDialog({
  orderId,
  count,
  open,
  onOpenChange,
}: {
  orderId: number;
  count: number;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const t = useTranslations("crm");
  const query = useCrmClientOrders(orderId, open);
  if (open && query.isError) {
    throw query.error;
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="w-[min(440px,calc(100vw-1.5rem))]">
        <div className="border-b border-[var(--line)] px-5 py-4 pr-14">
          <DialogTitle className="text-base font-semibold text-[var(--ink)]">
            {t("clientOrdersTitle", { count })}
          </DialogTitle>
        </div>
        {query.isSuccess ? (
          <div className="max-h-[60vh] divide-y divide-[var(--line)] overflow-y-auto">
            {query.data.orders.map((order) => (
              <ClientOrderRow
                key={order.id}
                order={order}
                current={order.id === orderId}
                onOpen={() => onOpenChange(false)}
              />
            ))}
          </div>
        ) : (
          <div className="flex h-24 items-center justify-center">
            <Spinner className="h-5 w-5" />
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
