"use client";

import { useTranslations } from "next-intl";
import { Bar, BarChart, CartesianGrid, Tooltip, XAxis, YAxis } from "recharts";
import { Spinner } from "@/components/ui/spinner";
import { useAnalyticsProducts } from "@/hooks/useAnalytics";
import { useFinancePeriod } from "@/hooks/useFinancePeriod";
import {
  AXIS_TICK,
  COLOR_ORDERS,
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
    label: t(KIND_LABELS[row.kind]),
    quantity: row.quantity,
  }));
  const weights = report.weights.map((row) => ({
    label: row.kg,
    quantity: row.quantity,
  }));

  return (
    <>
      <Note>{t("weightUnknown", { count: report.weight_unknown })}</Note>
      <Section title={t("productKinds")}>
        <ChartFrame>
          <BarChart data={kinds} margin={{ top: 16, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid stroke="#e8ddcd" vertical={false} />
            <XAxis dataKey="label" tick={AXIS_TICK} />
            <YAxis tick={AXIS_TICK} width={36} allowDecimals={false} />
            <Tooltip contentStyle={TOOLTIP_STYLE} />
            <Bar dataKey="quantity" name={t("quantity")} fill={COLOR_ORDERS} radius={[4, 4, 0, 0]} />
          </BarChart>
        </ChartFrame>
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
      <Section title={t("productPositions")}>
        <Rows
          rows={report.positions.map((row) => ({
            key: `${row.kind}:${row.name}`,
            label: row.name,
            extra: t(KIND_LABELS[row.kind]),
            quantity: row.quantity,
            orders: row.orders,
            kilograms: row.kilograms,
          }))}
        />
      </Section>
      <Section title={t("productFillings")}>
        <Rows
          rows={report.fillings.map((row) => ({
            key: row.filling,
            label: row.filling,
            extra: null,
            quantity: row.quantity,
            orders: row.orders,
            kilograms: row.kilograms,
          }))}
        />
      </Section>
    </>
  );
}

function Rows({
  rows,
}: {
  rows: {
    key: string;
    label: string;
    extra: string | null;
    quantity: number;
    orders: number;
    kilograms: string;
  }[];
}) {
  const t = useTranslations("analytics");
  if (rows.length === 0) return <Note>{t("emptyValue")}</Note>;
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="text-left text-xs uppercase tracking-wide text-[var(--muted)]">
            <th className="py-2 pr-3 font-medium">{t("name")}</th>
            <th className="py-2 pr-3 text-right font-medium">{t("quantity")}</th>
            <th className="py-2 pr-3 text-right font-medium">{t("orders")}</th>
            <th className="py-2 text-right font-medium">{t("kilograms")}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.key} className="border-t border-[var(--line)]">
              <td className="py-2 pr-3">
                {row.label}
                {row.extra ? <span className="mt-0.5 block text-xs text-[var(--muted)]">{row.extra}</span> : null}
              </td>
              <td className="py-2 pr-3 text-right tabular-nums">{row.quantity}</td>
              <td className="py-2 pr-3 text-right tabular-nums">{row.orders}</td>
              <td className="py-2 text-right tabular-nums">{row.kilograms}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
