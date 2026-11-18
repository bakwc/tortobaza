"use client";

import { useTranslations } from "next-intl";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Spinner } from "@/components/ui/spinner";
import { SharePie } from "@/components/analytics/SharePie";
import {
  AXIS_TICK,
  COLOR_REVENUE,
  Metric,
  Note,
  Section,
  TOOLTIP_STYLE,
} from "@/components/analytics/widgets";
import { useAnalyticsCogs } from "@/hooks/useAnalytics";
import { useFinancePeriod } from "@/hooks/useFinancePeriod";
import { formatAmount, formatMoney } from "@/lib/format";
import type { AnalyticsCogs } from "@/lib/api/types";

const NO_TECH_CARD = "no_tech_card";
const INGREDIENT_LIMIT = 20;
const TECH_CARD_LIMIT = 15;

export function CogsPanel() {
  const t = useTranslations("analytics");
  const period = useFinancePeriod();
  const query = useAnalyticsCogs(period.month);

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
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Metric label={t("cogsFoodCost")} value={formatMoney(report.food_cost, "GEL")} hint={null} />
        <Metric label={t("cogsRevenue")} value={formatMoney(report.revenue, "GEL")} hint={null} />
        <Metric label={t("cogsShare")} value={percent(report.food_cost_share)} hint={null} />
        <Metric
          label={t("cogsCoverage")}
          value={`${report.coverage.with_cost} / ${report.coverage.orders}`}
          hint={null}
        />
      </div>
      {report.coverage.with_cost === 0 ? <Note>{t("cogsEmpty")}</Note> : <CogsReport report={report} />}
    </div>
  );
}

function CogsReport({ report }: { report: AnalyticsCogs }) {
  const t = useTranslations("analytics");
  const units = useTranslations("stock.units");
  const categoryLabel = (name: string) => {
    if (name === "") return t("noCategory");
    if (name === NO_TECH_CARD) return t("noTechCard");
    return name;
  };
  const ingredients = report.ingredients.slice(0, INGREDIENT_LIMIT).map((row) => ({
    label: row.name,
    cost: Number(row.cost),
  }));
  const categories = report.categories.map((row) => ({
    key: row.name === "" ? "category" : row.name,
    label: categoryLabel(row.name),
    value: Number(row.cost),
  }));
  const cards = report.tech_cards.slice(0, TECH_CARD_LIMIT).map((row) => ({
    label: row.name === "" ? t("emptyValue") : row.name,
    cost: Number(row.cost),
  }));

  return (
    <>
      <Section title={t("cogsIngredients")}>
        <CostBars rows={ingredients} name={t("cogsCost")} />
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="text-left text-xs uppercase tracking-wide text-[var(--muted)]">
                <th className="py-2 pr-3 font-medium">{t("cogsIngredient")}</th>
                <th className="py-2 pr-3 font-medium">{t("category")}</th>
                <th className="py-2 pr-3 text-right font-medium">{t("quantity")}</th>
                <th className="py-2 pr-3 text-right font-medium">{t("cogsCost")}</th>
                <th className="py-2 text-right font-medium">{t("cogsShareOfCost")}</th>
              </tr>
            </thead>
            <tbody>
              {report.ingredients.map((row, index) => (
                <tr key={`${index}:${row.name}`} className="border-t border-[var(--line)]">
                  <td className="py-2 pr-3">{row.name}</td>
                  <td className="py-2 pr-3">{categoryLabel(row.category)}</td>
                  <td className="py-2 pr-3 text-right tabular-nums">
                    {formatAmount(row.quantity)} {units(row.unit)}
                  </td>
                  <td className="py-2 pr-3 text-right tabular-nums">{formatMoney(row.cost, "GEL")}</td>
                  <td className="py-2 text-right tabular-nums">{percent(row.share)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>
      <Section title={t("cogsCategories")}>
        <SharePie rows={categories} collapse={false} restLabel="" />
      </Section>
      <Section title={t("cogsTechCards")}>
        <CostBars rows={cards} name={t("cogsCost")} />
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="text-left text-xs uppercase tracking-wide text-[var(--muted)]">
                <th className="py-2 pr-3 font-medium">{t("techCard")}</th>
                <th className="py-2 pr-3 font-medium">{t("category")}</th>
                <th className="py-2 pr-3 text-right font-medium">{t("pieces")}</th>
                <th className="py-2 pr-3 text-right font-medium">{t("cogsCost")}</th>
                <th className="py-2 pr-3 text-right font-medium">{t("revenue")}</th>
                <th className="py-2 text-right font-medium">{t("cogsShareOfRevenue")}</th>
              </tr>
            </thead>
            <tbody>
              {report.tech_cards.map((row) => (
                <tr key={`${row.name}:${row.category}`} className="border-t border-[var(--line)]">
                  <td className="py-2 pr-3">{row.name === "" ? t("emptyValue") : row.name}</td>
                  <td className="py-2 pr-3">{categoryLabel(row.category)}</td>
                  <td className="py-2 pr-3 text-right tabular-nums">{formatAmount(row.quantity)}</td>
                  <td className="py-2 pr-3 text-right tabular-nums">{formatMoney(row.cost, "GEL")}</td>
                  <td className="py-2 pr-3 text-right tabular-nums">{formatMoney(row.revenue, "GEL")}</td>
                  <td className="py-2 text-right tabular-nums">{percent(row.share)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>
    </>
  );
}

function CostBars({ rows, name }: { rows: { label: string; cost: number }[]; name: string }) {
  return (
    <div className="w-full min-w-0" style={{ height: Math.max(288, rows.length * 32) }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={rows} layout="vertical" margin={{ top: 8, right: 16, left: 8, bottom: 0 }}>
          <CartesianGrid stroke="#e8ddcd" horizontal={false} />
          <XAxis type="number" tick={AXIS_TICK} />
          <YAxis type="category" dataKey="label" tick={AXIS_TICK} width={220} />
          <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(value) => formatMoney(Number(value), "GEL")} />
          <Bar dataKey="cost" name={name} fill={COLOR_REVENUE} radius={[0, 4, 4, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function percent(share: string): string {
  return `${Math.round(Number(share) * 100)}%`;
}
