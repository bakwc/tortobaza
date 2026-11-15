"use client";

import { useTranslations } from "next-intl";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Spinner } from "@/components/ui/spinner";
import { useAnalyticsProducts } from "@/hooks/useAnalytics";
import { useFinancePeriod } from "@/hooks/useFinancePeriod";
import { SharePie } from "@/components/analytics/SharePie";
import {
  AXIS_TICK,
  COLOR_REVENUE,
  ChartFrame,
  Metric,
  Note,
  Section,
  TOOLTIP_STYLE,
} from "@/components/analytics/widgets";
import { formatAmount } from "@/lib/format";
import type { AnalyticsProducts } from "@/lib/api/types";

const NO_TECH_CARD = "no_tech_card";
const TOP_LIMIT = 15;

export function ProductsPanel() {
  const t = useTranslations("analytics");
  const period = useFinancePeriod();
  const query = useAnalyticsProducts(period.month);

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
  return (
    <div className="grid gap-6">
      <Metric
        label={t("coverage")}
        value={`${report.coverage.with_items} / ${report.coverage.orders}`}
        hint={null}
      />
      {report.coverage.with_items === 0 ? (
        <Note>{t("productsEmpty")}</Note>
      ) : (
        <ProductsReport report={report} />
      )}
    </div>
  );
}

function ProductsReport({ report }: { report: AnalyticsProducts }) {
  const t = useTranslations("analytics");
  const categoryLabel = (name: string) => {
    if (name === "") return t("noCategory");
    if (name === NO_TECH_CARD) return t("noTechCard");
    return name;
  };
  const top = report.tech_cards.slice(0, TOP_LIMIT).map((row) => ({
    label: row.name,
    quantity: row.quantity,
  }));
  const categories = report.categories.map((row) => ({
    key: row.name === "" ? "category" : row.name,
    label: categoryLabel(row.name),
    value: row.quantity,
  }));
  const weights = report.weights.map((row) => ({
    label: row.kg,
    quantity: row.quantity,
  }));
  const pairs = report.cross_sales.pairs.map((pair) => ({
    label: `${categoryLabel(pair.first)} + ${categoryLabel(pair.second)}`,
    orders: pair.orders,
  }));

  return (
    <>
      <Note>{t("weightUnknown", { count: report.weight_unknown })}</Note>
      <Section title={t("productTechCards")}>
        <RankBars rows={top} dataKey="quantity" name={t("pieces")} />
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="text-left text-xs uppercase tracking-wide text-[var(--muted)]">
                <th className="py-2 pr-3 font-medium">{t("techCard")}</th>
                <th className="py-2 pr-3 font-medium">{t("category")}</th>
                <th className="py-2 pr-3 text-right font-medium">{t("pieces")}</th>
                <th className="py-2 pr-3 text-right font-medium">{t("share")}</th>
                <th className="py-2 pr-3 text-right font-medium">{t("orders")}</th>
                <th className="py-2 text-right font-medium">{t("kilograms")}</th>
              </tr>
            </thead>
            <tbody>
              {report.tech_cards.map((row) => (
                <tr key={`${row.name}:${row.category}`} className="border-t border-[var(--line)]">
                  <td className="py-2 pr-3">{row.name === "" ? t("emptyValue") : row.name}</td>
                  <td className="py-2 pr-3">{categoryLabel(row.category)}</td>
                  <td className="py-2 pr-3 text-right tabular-nums">{formatAmount(row.quantity)}</td>
                  <td className="py-2 pr-3 text-right tabular-nums">{Math.round(Number(row.share) * 100)}%</td>
                  <td className="py-2 pr-3 text-right tabular-nums">{formatAmount(row.orders)}</td>
                  <td className="py-2 text-right tabular-nums">{row.kilograms}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>
      <Section title={t("productCategories")}>
        <SharePie rows={categories} collapse={false} restLabel="" />
      </Section>
      <Section title={t("productWeights")}>
        <ChartFrame>
          <BarChart data={weights} margin={{ top: 16, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid stroke="#e8ddcd" vertical={false} />
            <XAxis dataKey="label" tick={AXIS_TICK} />
            <YAxis tick={AXIS_TICK} width={36} allowDecimals={false} />
            <Tooltip contentStyle={TOOLTIP_STYLE} />
            <Bar dataKey="quantity" name={t("quantity")} fill={COLOR_REVENUE} radius={[4, 4, 0, 0]} />
          </BarChart>
        </ChartFrame>
      </Section>
      {report.modifier_groups.map((group) => {
        const share = group.available === 0 ? 0 : Math.round((group.selected / group.available) * 100);
        return (
          <Section key={group.name} title={group.name}>
            <Note>
              {t("modifierSelected", { selected: group.selected, available: group.available, share })}
            </Note>
            {group.average !== null ? <Note>{t("modifierAverage", { average: group.average })}</Note> : null}
            <SharePie
              rows={group.modifiers.map((row) => ({
                key: row.name,
                label: row.name,
                value: row.quantity,
              }))}
              collapse
              restLabel={t("otherShare")}
            />
          </Section>
        );
      })}
      <Section title={t("crossSales")}>
        <Metric
          label={t("multiCategoryOrders")}
          value={`${report.cross_sales.multi_category} / ${report.cross_sales.orders}`}
          hint={null}
        />
        {pairs.length === 0 ? (
          <Note>{t("emptyValue")}</Note>
        ) : (
          <RankBars rows={pairs} dataKey="orders" name={t("orders")} />
        )}
      </Section>
    </>
  );
}

function RankBars({
  rows,
  dataKey,
  name,
}: {
  rows: { label: string; quantity?: number; orders?: number }[];
  dataKey: "quantity" | "orders";
  name: string;
}) {
  return (
    <div className="w-full min-w-0" style={{ height: Math.max(288, rows.length * 32) }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={rows} layout="vertical" margin={{ top: 8, right: 16, left: 8, bottom: 0 }}>
          <CartesianGrid stroke="#e8ddcd" horizontal={false} />
          <XAxis type="number" tick={AXIS_TICK} allowDecimals={false} />
          <YAxis type="category" dataKey="label" tick={AXIS_TICK} width={220} />
          <Tooltip contentStyle={TOOLTIP_STYLE} />
          <Bar dataKey={dataKey} name={name} fill={COLOR_REVENUE} radius={[0, 4, 4, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
