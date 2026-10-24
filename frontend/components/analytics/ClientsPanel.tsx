"use client";

import { useLocale, useTranslations } from "next-intl";
import { Bar, BarChart, CartesianGrid, Legend, Tooltip, XAxis, YAxis } from "recharts";
import { Spinner } from "@/components/ui/spinner";
import { useAnalyticsClients } from "@/hooks/useAnalytics";
import { Link } from "@/i18n/navigation";
import { formatAmount, formatMoney } from "@/lib/format";
import type { AnalyticsCustomer, AnalyticsLapsed } from "@/lib/api/types";
import {
  AXIS_TICK,
  COLOR_NEW,
  COLOR_ORDERS,
  COLOR_REVENUE,
  ChartFrame,
  Metric,
  Note,
  Section,
  TOOLTIP_STYLE,
  dayLabel,
  monthLabel,
} from "@/components/analytics/widgets";

export function ClientsPanel() {
  const t = useTranslations("analytics");
  const locale = useLocale();
  const query = useAnalyticsClients();

  if (query.isError) {
    return <p className="text-sm text-[var(--danger)]">{t("loadError")}</p>;
  }
  if (!query.data) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center">
        <Spinner className="h-6 w-6 text-[var(--brand)]" />
      </div>
    );
  }

  const report = query.data;
  const orders = report.months.map((row) => ({
    label: monthLabel(row.month, locale),
    newOrders: row.new_orders,
    returnOrders: row.return_orders,
  }));
  const revenue = report.months.map((row) => ({
    label: monthLabel(row.month, locale),
    newRevenue: Number(row.new_revenue),
    returnRevenue: Number(row.return_revenue),
  }));
  const gaps = report.gaps.bins.map((bin) => ({ label: bin.label, count: bin.count }));
  const frequency = [
    { label: t("once"), clients: report.frequency.once.clients },
    { label: t("twice"), clients: report.frequency.twice.clients },
    { label: t("more"), clients: report.frequency.more.clients },
  ];
  const repeatHint =
    Number(report.known_revenue) === 0
      ? null
      : t("repeatRevenue", {
          share: Math.round((Number(report.repeat_revenue) / Number(report.known_revenue)) * 100),
        });
  const header = report.cohorts[0];

  return (
    <div className="grid gap-6">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Metric label={t("clientsTitle")} value={formatAmount(report.clients)} hint={null} />
        <Metric label={t("repeatClients")} value={formatAmount(report.repeat_clients)} hint={repeatHint} />
        <Metric label={t("knownOrders")} value={formatAmount(report.known_orders)} hint={null} />
        <Metric label={t("unknownClients")} value={formatAmount(report.unknown_orders)} hint={null} />
      </div>
      <Note>{t("clientsNote", { count: report.unknown_orders })}</Note>
      <Section title={t("byMonthOrders")}>
        <ChartFrame>
          <BarChart data={orders} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid stroke="#e8ddcd" vertical={false} />
            <XAxis dataKey="label" tick={AXIS_TICK} />
            <YAxis tick={AXIS_TICK} width={36} />
            <Tooltip contentStyle={TOOLTIP_STYLE} />
            <Legend />
            <Bar dataKey="newOrders" name={t("newClients")} stackId="orders" fill={COLOR_NEW} />
            <Bar dataKey="returnOrders" name={t("returning")} stackId="orders" fill={COLOR_REVENUE} />
          </BarChart>
        </ChartFrame>
      </Section>
      <Section title={t("byMonthRevenue")}>
        <ChartFrame>
          <BarChart data={revenue} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid stroke="#e8ddcd" vertical={false} />
            <XAxis dataKey="label" tick={AXIS_TICK} />
            <YAxis tick={AXIS_TICK} width={48} />
            <Tooltip contentStyle={TOOLTIP_STYLE} />
            <Legend />
            <Bar dataKey="newRevenue" name={t("newClients")} stackId="revenue" fill={COLOR_NEW} />
            <Bar dataKey="returnRevenue" name={t("returning")} stackId="revenue" fill={COLOR_REVENUE} />
          </BarChart>
        </ChartFrame>
      </Section>
      <Section title={t("cohorts")}>
        <Note>{t("cohortNote")}</Note>
        {header ? (
          <div className="overflow-x-auto">
            <table className="border-separate border-spacing-2 text-sm">
              <thead>
                <tr>
                  <th />
                  {header.cells.map((cell) => (
                    <th key={cell.offset} className="px-2 text-xs font-medium text-[var(--muted)]">
                      {t("cohortOffset", { offset: cell.offset })}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {report.cohorts.map((row) => (
                  <tr key={row.month}>
                    <th className="whitespace-nowrap pr-3 text-left font-medium text-[var(--ink)]">
                      {monthLabel(row.month, locale)}
                      <span className="mt-0.5 block text-xs font-normal text-[var(--muted)]">
                        {t("cohortClients", { count: row.clients })}
                      </span>
                    </th>
                    {row.cells.map((cell) => (
                      <td key={cell.offset}>
                        {cell.observed && cell.count !== null && cell.share !== null ? (
                          <span
                            className="flex min-h-12 min-w-16 flex-col items-center justify-center rounded-lg px-2 py-1"
                            style={{ background: `rgba(204, 118, 127, ${Math.min(1, Number(cell.share))})` }}
                          >
                            <b>{Math.round(Number(cell.share) * 100)}%</b>
                            <small>{cell.count}</small>
                          </span>
                        ) : (
                          <span className="flex min-h-12 min-w-16 items-center justify-center rounded-lg bg-[var(--cream)] text-[var(--muted)]">
                            {t("emptyValue")}
                          </span>
                        )}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <Note>{t("emptyValue")}</Note>
        )}
      </Section>
      <Section title={t("gap")}>
        <Note>
          {report.gaps.median === null
            ? t("gapEmpty")
            : t("gapMedian", { days: formatAmount(report.gaps.median) })}
        </Note>
        <ChartFrame>
          <BarChart data={gaps} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid stroke="#e8ddcd" vertical={false} />
            <XAxis dataKey="label" tick={AXIS_TICK} />
            <YAxis tick={AXIS_TICK} width={36} allowDecimals={false} />
            <Tooltip contentStyle={TOOLTIP_STYLE} />
            <Bar dataKey="count" name={t("clientsTitle")} fill={COLOR_REVENUE} radius={[4, 4, 0, 0]} />
          </BarChart>
        </ChartFrame>
      </Section>
      <Section title={t("frequency")}>
        <div className="grid gap-3 sm:grid-cols-3">
          <Metric
            label={t("once")}
            value={formatAmount(report.frequency.once.clients)}
            hint={formatMoney(report.frequency.once.revenue, "GEL")}
          />
          <Metric
            label={t("twice")}
            value={formatAmount(report.frequency.twice.clients)}
            hint={formatMoney(report.frequency.twice.revenue, "GEL")}
          />
          <Metric
            label={t("more")}
            value={formatAmount(report.frequency.more.clients)}
            hint={formatMoney(report.frequency.more.revenue, "GEL")}
          />
        </div>
        <ChartFrame>
          <BarChart data={frequency} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid stroke="#e8ddcd" vertical={false} />
            <XAxis dataKey="label" tick={AXIS_TICK} />
            <YAxis tick={AXIS_TICK} width={36} allowDecimals={false} />
            <Tooltip contentStyle={TOOLTIP_STYLE} />
            <Bar dataKey="clients" name={t("clientsTitle")} fill={COLOR_ORDERS} radius={[4, 4, 0, 0]} />
          </BarChart>
        </ChartFrame>
      </Section>
      <Section title={t("topRevenue")}>
        <CustomerTable rows={report.top_revenue} />
      </Section>
      <Section title={t("topOrders")}>
        <CustomerTable rows={report.top_orders} />
      </Section>
      <Section title={t("lapsed")}>
        <Note>{t("lapsedNote")}</Note>
        {report.lapsed.length === 0 ? (
          <Note>{t("lapsedEmpty")}</Note>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-sm">
              <thead>
                <tr className="text-left text-xs uppercase tracking-wide text-[var(--muted)]">
                  <th className="py-2 pr-3 font-medium">{t("name")}</th>
                  <th className="py-2 pr-3 font-medium">{t("phone")}</th>
                  <th className="py-2 pr-3 text-right font-medium">{t("revenue")}</th>
                  <th className="py-2 font-medium">{t("date")}</th>
                </tr>
              </thead>
              <tbody>
                {report.lapsed.map((row) => (
                  <LapsedRow key={row.order_id} row={row} locale={locale} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Section>
    </div>
  );
}

function CustomerTable({ rows }: { rows: AnalyticsCustomer[] }) {
  const t = useTranslations("analytics");
  const locale = useLocale();
  if (rows.length === 0) return <Note>{t("emptyValue")}</Note>;
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="text-left text-xs uppercase tracking-wide text-[var(--muted)]">
            <th className="py-2 pr-3 font-medium">{t("name")}</th>
            <th className="py-2 pr-3 font-medium">{t("phone")}</th>
            <th className="py-2 pr-3 text-right font-medium">{t("orders")}</th>
            <th className="py-2 pr-3 text-right font-medium">{t("revenue")}</th>
            <th className="py-2 pr-3 font-medium">{t("first")}</th>
            <th className="py-2 font-medium">{t("last")}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.order_id} className="border-t border-[var(--line)]">
              <td className="py-2 pr-3">
                <ClientLink row={row} />
              </td>
              <td className="py-2 pr-3 tabular-nums">{row.phones.join(", ")}</td>
              <td className="py-2 pr-3 text-right tabular-nums">{row.orders}</td>
              <td className="py-2 pr-3 text-right tabular-nums">{formatMoney(row.revenue, "GEL")}</td>
              <td className="py-2 pr-3">{dayLabel(row.first, locale)}</td>
              <td className="py-2">{dayLabel(row.last, locale)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function LapsedRow({ row, locale }: { row: AnalyticsLapsed; locale: string }) {
  return (
    <tr className="border-t border-[var(--line)]">
      <td className="py-2 pr-3">
        <ClientLink row={row} />
      </td>
      <td className="py-2 pr-3 tabular-nums">{row.phones.join(", ")}</td>
      <td className="py-2 pr-3 text-right tabular-nums">{formatMoney(row.revenue, "GEL")}</td>
      <td className="py-2">{dayLabel(row.date, locale)}</td>
    </tr>
  );
}

function ClientLink({ row }: { row: { name: string; order_id: number } }) {
  const t = useTranslations("analytics");
  return (
    <Link href={`/crm/${row.order_id}/edit`} className="font-medium text-[var(--brand)]">
      {row.name === "" ? t("emptyValue") : row.name}
    </Link>
  );
}
