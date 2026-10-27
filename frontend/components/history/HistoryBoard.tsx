"use client";

import { Suspense, type FormEvent } from "react";
import { useSearchParams } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { SectionShell, type SectionTab } from "@/components/menu/SectionShell";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { useAuditEvents } from "@/hooks/useAuditEvents";
import { Link, useRouter } from "@/i18n/navigation";
import type { AuditEvent } from "@/lib/api/types";

const APPS = ["menu", "inventory", "crm", "rsge", "catalog", "orders", "accounts", "attendance"] as const;

const ORDER_FIELDS: Record<string, string> = {
  date: "dateLabel",
  time_start: "timeStart",
  time_end: "timeEnd",
  when_ready: "timeWhenReady",
  contact: "contact",
  is_gift: "gift",
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
  delivery_price: "delivery",
  prepayment: "prepaid",
  is_paid: "paid",
  payment_type: "paymentMethod",
  payment_date: "paymentDate",
  website_order_id: "historyFieldWebsiteOrder",
  flowwow_order_id: "historyFieldFlowwowOrder",
  deleted: "historyFieldDeleted",
  images: "imagesSection",
};

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

function formatWhen(iso: string, locale: string): string {
  return new Date(iso).toLocaleString(historyLocale(locale), {
    timeZone: "Asia/Tbilisi",
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatValue(value: unknown): string {
  if (value === null) return "null";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return JSON.stringify(value);
}

function fieldLabel(field: string, event: AuditEvent, t: (key: string) => string): string {
  if (event.app_label === "crm" && event.model === "crmorder" && field in ORDER_FIELDS) {
    return t(ORDER_FIELDS[field]);
  }
  return field;
}

function queryHref(params: URLSearchParams): string {
  const query = params.toString();
  return query ? `/history?${query}` : "/history";
}

export function HistoryBoard() {
  return (
    <Suspense
      fallback={
        <div className="mx-auto flex min-h-[40vh] w-full max-w-5xl items-center justify-center px-4 py-8">
          <Spinner className="h-6 w-6 text-[var(--brand)]" />
        </div>
      }
    >
      <HistoryBoardContent />
    </Suspense>
  );
}

function HistoryBoardContent() {
  const t = useTranslations("operationHistory");
  const tCrm = useTranslations("crm");
  const locale = useLocale();
  const router = useRouter();
  const searchParams = useSearchParams();
  const page = Number(searchParams.get("page") ?? "1");
  const start = searchParams.get("start") ?? "";
  const end = searchParams.get("end") ?? "";
  const app = searchParams.get("app") ?? "";
  const q = searchParams.get("q") ?? "";
  const query = useAuditEvents({
    page: Number.isFinite(page) && page > 0 ? page : 1,
    start,
    end,
    app,
    q,
  });
  const tabs: SectionTab[] = [{ key: "history", href: "/history", label: t("title") }];

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const params = new URLSearchParams();
    for (const key of ["start", "end", "app", "q"]) {
      const value = String(data.get(key) ?? "");
      if (value) params.set(key, value);
    }
    router.replace(queryHref(params));
  };

  return (
    <SectionShell active="history" financeOnly tabs={tabs}>
      <form onSubmit={onSubmit} className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        <label className="grid gap-1 text-sm text-[var(--ink)]">
          {t("start")}
          <input
            name="start"
            type="date"
            defaultValue={start}
            className="h-10 rounded-xl border border-[var(--line)] bg-white px-3"
          />
        </label>
        <label className="grid gap-1 text-sm text-[var(--ink)]">
          {t("end")}
          <input
            name="end"
            type="date"
            defaultValue={end}
            className="h-10 rounded-xl border border-[var(--line)] bg-white px-3"
          />
        </label>
        <label className="grid gap-1 text-sm text-[var(--ink)]">
          {t("app")}
          <select
            name="app"
            defaultValue={app}
            className="h-10 rounded-xl border border-[var(--line)] bg-white px-3"
          >
            <option value="">{t("allApps")}</option>
            {APPS.map((item) => (
              <option key={item} value={item}>
                {t(`apps.${item}`)}
              </option>
            ))}
          </select>
        </label>
        <label className="grid gap-1 text-sm text-[var(--ink)] lg:col-span-2">
          {t("search")}
          <input
            name="q"
            type="search"
            defaultValue={q}
            className="h-10 rounded-xl border border-[var(--line)] bg-white px-3"
          />
        </label>
        <div className="sm:col-span-2 lg:col-span-5">
          <Button type="submit" size="sm">
            {t("apply")}
          </Button>
        </div>
      </form>
      {query.isPending ? (
        <div className="flex justify-center py-16">
          <Spinner className="h-6 w-6 text-[var(--brand)]" />
        </div>
      ) : null}
      {query.isError ? <p className="text-sm text-[var(--ink)]">{t("loadError")}</p> : null}
      {query.data && query.data.results.length === 0 ? (
        <p className="text-sm text-[var(--ink)]">{t("empty")}</p>
      ) : null}
      {query.data && query.data.results.length > 0 ? (
        <div className="grid gap-3">
          {query.data.results.map((event) => (
            <article key={event.id} className="grid gap-2 rounded-3xl border border-[var(--line)] bg-white p-4">
              <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1 text-sm text-[var(--ink)]">
                <time dateTime={event.created_at}>{formatWhen(event.created_at, locale)}</time>
                <span className="font-medium">{event.actor_name ?? t("system")}</span>
                <span>{tCrm(ACTION_KEYS[event.action])}</span>
                {event.source !== "user" ? <span>{tCrm(SOURCE_KEYS[event.source])}</span> : null}
                {event.database === "personal" ? (
                  <span className="rounded-full bg-[var(--cream)] px-2 py-0.5 text-xs">{t("personal")}</span>
                ) : null}
              </div>
              <p className="text-sm text-[var(--ink)]">
                <span className="text-[var(--ink)]/60">
                  {event.app_label}.{event.model} #{event.object_id}
                </span>{" "}
                {event.object_label}
              </p>
              <dl className="grid gap-1">
                {Object.entries(event.changes).map(([field, change]) => (
                  <div key={field} className="grid gap-0.5 text-sm text-[var(--ink)] sm:grid-cols-[12rem_1fr]">
                    <dt className="text-[var(--ink)]/60">{fieldLabel(field, event, tCrm)}</dt>
                    <dd className="break-all font-mono text-xs">
                      {formatValue(change.old)} → {formatValue(change.new)}
                    </dd>
                  </div>
                ))}
              </dl>
            </article>
          ))}
          <div className="flex items-center justify-between gap-3 text-sm text-[var(--ink)]">
            <span>{t("page", { page: query.data.page, pages: query.data.pages })}</span>
            <div className="flex gap-2">
              {query.data.page > 1 ? (
                <Button asChild variant="outline" size="sm">
                  <Link href={pageHref(searchParams, query.data.page - 1)}>{t("previous")}</Link>
                </Button>
              ) : null}
              {query.data.page < query.data.pages ? (
                <Button asChild variant="outline" size="sm">
                  <Link href={pageHref(searchParams, query.data.page + 1)}>{t("next")}</Link>
                </Button>
              ) : null}
            </div>
          </div>
        </div>
      ) : null}
    </SectionShell>
  );
}

function pageHref(searchParams: { toString(): string }, page: number): string {
  const params = new URLSearchParams(searchParams.toString());
  params.set("page", String(page));
  return queryHref(params);
}
