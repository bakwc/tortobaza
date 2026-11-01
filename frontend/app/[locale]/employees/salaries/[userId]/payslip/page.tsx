"use client";

import { Suspense } from "react";
import { useParams, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { CrmAuthGate } from "@/components/crm/CrmAuthGate";
import { PayslipDocument } from "@/components/employees/PayslipDocument";
import { Spinner } from "@/components/ui/spinner";
import { useCrmSalaries } from "@/hooks/useCrmOrders";

const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;

function PayslipBody({ userId }: { userId: number }) {
  const t = useTranslations("crm");
  const searchParams = useSearchParams();
  const start = searchParams.get("start") ?? "";
  const end = searchParams.get("end") ?? "";
  const rangeReady = ISO_DATE.test(start) && ISO_DATE.test(end);
  const month = rangeReady ? start.slice(0, 7) : "";
  const salariesQuery = useCrmSalaries(month);

  if (!Number.isFinite(userId) || userId < 1 || !rangeReady) {
    return <p className="text-sm text-[var(--danger)]">{t("salaryLoadError")}</p>;
  }

  if (salariesQuery.isError) {
    return <p className="text-sm text-[var(--danger)]">{t("salaryLoadError")}</p>;
  }

  if (!salariesQuery.data) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center">
        <Spinner className="h-6 w-6 text-[var(--brand)]" />
      </div>
    );
  }

  const period = salariesQuery.data.periods.find((row) => row.start === start && row.end === end);
  const employee = period?.employees.find((row) => row.id === userId);
  if (!period || !employee) {
    return <p className="text-sm text-[var(--danger)]">{t("salaryLoadError")}</p>;
  }

  return (
    <PayslipDocument
      name={employee.name}
      position={employee.position}
      start={period.start}
      end={period.end}
      hours={employee.hours}
      money={employee.money}
    />
  );
}

export default function SalaryPayslipPage() {
  const params = useParams<{ userId: string }>();
  const userId = Number(params.userId);

  return (
    <div className="mx-auto w-full max-w-[210mm] px-4 py-8 md:py-12 print:px-0 print:py-0">
      <CrmAuthGate>
        <Suspense>
          <PayslipBody userId={userId} />
        </Suspense>
      </CrmAuthGate>
    </div>
  );
}
