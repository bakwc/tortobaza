"use client";

import { useLocale, useTranslations } from "next-intl";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { Spinner } from "@/components/ui/spinner";
import { useCrmOrderEvents } from "@/hooks/useCrmOrders";
import type { CrmOrderEvent, CrmOrderStatus } from "@/lib/api/types";
import { CRM_ORDER_STATUS_MESSAGE_KEYS } from "@/lib/crmStatus";
import { formatAed, formatTimeslotDateLabel } from "@/lib/format";

const HISTORY_FIELDS = [
  "date",
  "time_start",
  "time_end",
  "when_ready",
  "contact",
  "nickname",
  "delivery_address",
  "fulfillment_type",
  "status",
  "taken_by_id",
  "created_by_id",
  "delivered_by_id",
  "weight",
  "filling",
  "description",
  "internal_description",
  "cake_price",
  "prepayment",
  "is_paid",
  "payment_type",
  "website_order_id",
  "flowwow_order_id",
  "deleted",
  "images",
] as const;

const HISTORY_FIELD_KEYS = {
  date: "dateLabel",
  time_start: "timeStart",
  time_end: "timeEnd",
  when_ready: "timeWhenReady",
  contact: "contact",
  nickname: "nickname",
  delivery_address: "deliveryAddress",
  fulfillment_type: "fulfillmentLabel",
  status: "historyFieldStatus",
  taken_by_id: "historyFieldTakenBy",
  created_by_id: "historyFieldCreatedBy",
  delivered_by_id: "historyFieldDeliveredBy",
  weight: "weight",
  filling: "filling",
  description: "notes",
  internal_description: "internalNotes",
  cake_price: "price",
  prepayment: "prepaid",
  is_paid: "paid",
  payment_type: "paymentMethod",
  website_order_id: "historyFieldWebsiteOrder",
  flowwow_order_id: "historyFieldFlowwowOrder",
  deleted: "historyFieldDeleted",
  images: "imagesSection",
} as const;

const ACTION_KEYS = {
  created: "historyActionCreated",
  updated: "historyActionUpdated",
  deleted: "historyActionDeleted",
} as const;

const SOURCE_KEYS = {
  crm: "historySourceCrm",
  admin: "historySourceAdmin",
  website: "historySourceWebsite",
  flowwow: "historySourceFlowwow",
} as const;

function historyLocale(locale: string): string {
  if (locale === "ka") return "ka-GE";
  if (locale === "ru") return "ru-RU";
  return "en-GB";
}

function formatHistoryWhen(iso: string, locale: string): string {
  return new Date(iso).toLocaleString(historyLocale(locale), {
    timeZone: "Asia/Tbilisi",
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function fileName(path: string): string {
  const parts = path.split("/");
  return parts[parts.length - 1] ?? path;
}

function isUserRef(value: unknown): value is {
  id: number;
  name: string | null;
  telegram_url: string | null;
} {
  if (typeof value !== "object" || value === null) return false;
  return "id" in value && "name" in value;
}

function isCrmStatus(value: string): value is CrmOrderStatus {
  return value in CRM_ORDER_STATUS_MESSAGE_KEYS;
}

function paymentTypeLabel(type: string, t: (key: string) => string): string {
  if (type === "unknown") return t("paymentUnknown");
  if (type === "cash") return t("paymentCash");
  if (type === "terminal") return t("paymentTerminal");
  if (type === "tbc") return t("paymentTbc");
  if (type === "bog") return t("paymentBog");
  if (type === "flowwow") return t("paymentFlowwow");
  if (type === "crypto") return t("paymentCrypto");
  if (type === "online") return t("paymentOnline");
  return type;
}

function orderedChangeFields(changes: CrmOrderEvent["changes"]): string[] {
  const known = new Set<string>(HISTORY_FIELDS);
  return [
    ...HISTORY_FIELDS.filter((field) => field in changes),
    ...Object.keys(changes).filter((field) => !known.has(field)),
  ];
}

function CrmOrderHistoryBody({ orderId }: { orderId: number }) {
  const t = useTranslations("crm");
  const locale = useLocale();
  const events = useCrmOrderEvents(orderId, true);

  function fieldLabel(field: string): string {
    if (field in HISTORY_FIELD_KEYS) {
      return t(HISTORY_FIELD_KEYS[field as keyof typeof HISTORY_FIELD_KEYS]);
    }
    return field;
  }

  function formatValue(field: string, value: unknown) {
    if (value === null || value === "") return "—";
    if (isUserRef(value)) {
      const label = value.name ?? String(value.id);
      if (!value.telegram_url) return label;
      return (
        <a
          href={value.telegram_url}
          target="_blank"
          rel="noreferrer"
          className="underline"
        >
          {label}
        </a>
      );
    }
    if (typeof value === "boolean") {
      if (field === "is_paid") return value ? t("paid") : t("notPaid");
      return value ? t("historyYes") : t("historyNo");
    }
    if (Array.isArray(value)) {
      if (value.length === 0) return "—";
      return value.map((item) => fileName(String(item))).join(", ");
    }
    if (typeof value === "string") {
      if (field === "status" && isCrmStatus(value)) {
        return t(CRM_ORDER_STATUS_MESSAGE_KEYS[value]);
      }
      if (field === "fulfillment_type" && value === "delivery") return t("delivery");
      if (field === "fulfillment_type" && value === "pickup") return t("pickup");
      if (field === "payment_type") return paymentTypeLabel(value, t);
      if (field === "date") return formatTimeslotDateLabel(value, locale);
      if (field === "time_start" || field === "time_end") return value.slice(0, 5);
      if (field === "cake_price" || field === "prepayment") return formatAed(value);
      return value;
    }
    return String(value);
  }

  return (
    <div className="max-h-[calc(100vh-3rem)] overflow-y-auto p-6">
      <DialogTitle className="pr-10 text-lg font-semibold text-[var(--ink)]">
        {t("history")}
      </DialogTitle>
      {events.isPending ? (
        <div className="flex justify-center py-10">
          <Spinner className="h-5 w-5" />
        </div>
      ) : null}
      {events.isError ? (
        <p className="mt-4 text-sm text-[var(--danger)]">{t("historyLoadError")}</p>
      ) : null}
      {events.data && events.data.length === 0 ? (
        <p className="mt-4 text-sm text-[var(--muted-2)]">{t("historyEmpty")}</p>
      ) : null}
      {events.data && events.data.length > 0 ? (
        <ol className="mt-4 flex flex-col gap-4">
          {events.data.map((event) => {
            const fields = orderedChangeFields(event.changes);
            return (
              <li
                key={event.id}
                className="border-t border-[var(--line)] pt-4 first:border-t-0 first:pt-0"
              >
                <p className="text-sm font-medium text-[var(--ink)]">
                  {formatHistoryWhen(event.created_at, locale)}
                  {" · "}
                  {event.actor_name ? (
                    event.actor_telegram_url ? (
                      <a
                        href={event.actor_telegram_url}
                        target="_blank"
                        rel="noreferrer"
                        className="underline"
                      >
                        {event.actor_name}
                      </a>
                    ) : (
                      event.actor_name
                    )
                  ) : (
                    t(SOURCE_KEYS[event.source])
                  )}
                </p>
                <p className="mt-0.5 text-xs text-[var(--muted-2)]">
                  {t(ACTION_KEYS[event.action])}
                </p>
                <div className="mt-2 flex flex-col gap-1.5">
                  {fields.map((field) => {
                    const change = event.changes[field];
                    if (!change) return null;
                    return (
                      <p key={field} className="text-sm text-[var(--ink)]">
                        <span className="text-[var(--muted-2)]">{fieldLabel(field)}: </span>
                        <span className="whitespace-pre-wrap break-words">
                          {formatValue(field, change.old)}
                          {" → "}
                          {formatValue(field, change.new)}
                        </span>
                      </p>
                    );
                  })}
                </div>
              </li>
            );
          })}
        </ol>
      ) : null}
    </div>
  );
}

export function CrmOrderHistoryDialog({
  orderId,
  open,
  onOpenChange,
}: {
  orderId: number;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="w-[min(520px,calc(100vw-1.5rem))] max-w-[520px]">
        {open ? <CrmOrderHistoryBody orderId={orderId} /> : null}
      </DialogContent>
    </Dialog>
  );
}
