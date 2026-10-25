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
import type { AnalyticsProductKind, AnalyticsProducts } from "@/lib/api/types";

const KIND_LABELS: Record<AnalyticsProductKind, string> = {
  cake: "kindCake",
  bento: "kindBento",
  cupcake: "kindCupcake",
  macaron: "kindMacaron",
  addon: "kindAddon",
  other: "kindOther",
};

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
        value={`${report.coverage.parsed} / ${report.coverage.orders}`}
        hint={null}
      />
      {report.coverage.parsed === 0 ? (
        <Note>{t("productsEmpty")}</Note>
      ) : (
        <ProductsReport report={report} />
      )}
    </div>
  );
}

function ProductsReport({ report }: { report: AnalyticsProducts }) {
  const t = useTranslations("analytics");
  const kinds = report.kinds.map((row) => ({
    key: row.kind,
    label: t(KIND_LABELS[row.kind]),
    value: row.quantity,
  }));
  const fillings = report.fillings.map((row) => ({
    key: row.filling,
    label: row.filling,
    value: row.quantity,
  }));
  const weights = report.weights.map((row) => ({
    label: row.kg,
    quantity: row.quantity,
  }));

  return (
    <>
      <Note>{t("weightUnknown", { count: report.weight_unknown })}</Note>
      <Section title={t("productKinds")}>
        <SharePie rows={kinds} collapse={false} restLabel="" />
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
      <Section title={t("productFillings")}>
        {fillings.length === 0 ? (
          <Note>{t("emptyValue")}</Note>
        ) : (
          <SharePie rows={fillings} collapse restLabel={t("otherFillings")} />
        )}
      </Section>
    </>
  );
}
