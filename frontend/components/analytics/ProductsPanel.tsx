"use client";

import { useTranslations } from "next-intl";
import { Bar, BarChart, CartesianGrid, Tooltip, XAxis, YAxis } from "recharts";
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
import type { AnalyticsProducts } from "@/lib/api/types";

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
  const techCards = report.tech_cards.map((row) => ({
    key: row.name,
    label: row.name,
    value: row.quantity,
  }));
  const weights = report.weights.map((row) => ({
    label: row.kg,
    quantity: row.quantity,
  }));

  return (
    <>
      <Note>{t("weightUnknown", { count: report.weight_unknown })}</Note>
      <Section title={t("productTechCards")}>
        <SharePie rows={techCards} collapse restLabel={t("otherShare")} />
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
      {report.modifier_groups.map((group) => (
        <Section key={group.name} title={group.name}>
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
      ))}
    </>
  );
}
