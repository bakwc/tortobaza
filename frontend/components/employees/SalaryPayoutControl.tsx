"use client";

import { useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { useCan } from "@/hooks/useAuth";
import { useCreateSalaryPayout } from "@/hooks/useCrmOrders";
import { useFinanceAccounts } from "@/hooks/useFinanceTransactions";
import { Link } from "@/i18n/navigation";
import { apiErrorMessage } from "@/components/menu/ui";
import {
  INVALID_FIELDS_CLASS,
  clearCustomValidity,
  collectFieldProblems,
  formatFieldProblems,
} from "@/lib/formValidation";
import { cn } from "@/lib/utils";
import type { CrmSalaryPeriod } from "@/lib/api/types";
import { formatAed, formatCrmCompactDate, getTbilisiTodayIsoDate } from "@/lib/format";

const SELECT_CLASS =
  "h-12 w-full rounded-full border border-[var(--line)] bg-white px-5 text-sm text-[var(--ink)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--brand)]/30";

export function SalaryPayoutControl({
  employee,
  start,
  end,
}: {
  employee: CrmSalaryPeriod["employees"][number];
  start: string;
  end: string;
}) {
  const t = useTranslations("crm");
  const tForms = useTranslations("forms");
  const locale = useLocale();
  const canPay = useCan("edit_finance");
  const payout = employee.payout;
  const [open, setOpen] = useState(false);
  const [date, setDate] = useState(getTbilisiTodayIsoDate);
  const [accountId, setAccountId] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [validationShown, setValidationShown] = useState(false);
  const [messages, setMessages] = useState<string[]>([]);
  const accountsQuery = useFinanceAccounts(open, "business");
  const createPayout = useCreateSalaryPayout();

  if (payout !== null) {
    return (
      <Link
        href={`/finance?month=${payout.date.slice(0, 7)}&transaction=${payout.id}`}
        className="inline-flex items-center gap-1 rounded-full bg-violet-100 px-2 py-0.5 text-[10px] font-semibold text-violet-900 hover:opacity-90"
      >
        {t("salaryPaid")} {formatCrmCompactDate(payout.date, locale)} {formatAed(payout.amount)}{" "}
        {payout.counterparty_name}
      </Link>
    );
  }

  if (!canPay) return null;

  function openDialog() {
    setDate(getTbilisiTodayIsoDate());
    setAccountId("");
    setErrorMessage("");
    setOpen(true);
  }

  function onError(error: unknown) {
    setErrorMessage(apiErrorMessage(error, t("salaryPayError")) ?? t("salaryPayError"));
  }

  function submit() {
    setErrorMessage("");
    createPayout.mutate(
      {
        userId: employee.id,
        body: {
          start,
          end,
          account_id: Number(accountId),
          date,
        },
      },
      {
        onSuccess: () => setOpen(false),
        onError,
      },
    );
  }

  const accounts = accountsQuery.data ?? [];

  return (
    <>
      <Button type="button" variant="outline" size="sm" className="h-8" onClick={openDialog}>
        {t("salaryPay")}
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="w-[min(420px,calc(100vw-1.5rem))] p-6">
          <DialogTitle className="pr-10 text-base font-semibold text-[var(--ink)]">
            {t("salaryPayTitle")}: {employee.name}
          </DialogTitle>
          <form
            noValidate
            data-validated={validationShown ? "" : undefined}
            className={cn("mt-4 grid gap-4", INVALID_FIELDS_CLASS)}
            onSubmit={(event) => {
              event.preventDefault();
              clearCustomValidity(event.currentTarget);
              const next = formatFieldProblems(
                collectFieldProblems(event.currentTarget),
                (fields) => tForms("requiredFieldsMissing", { fields }),
                (fields) => tForms("invalidFormat", { fields }),
              );
              setValidationShown(true);
              setMessages(next);
              if (next.length > 0) return;
              submit();
            }}
          >
            <p className="text-sm font-semibold tabular-nums text-[var(--ink)]">{formatAed(employee.money)}</p>
            <label className="flex flex-col gap-1.5">
              <span className="text-xs font-medium uppercase tracking-wide text-[var(--ink)]/60">
                {t("salaryPayDate")}
              </span>
              <Input required type="date" value={date} onChange={(event) => setDate(event.target.value)} />
            </label>
            <label className="flex flex-col gap-1.5">
              <span className="text-xs font-medium uppercase tracking-wide text-[var(--ink)]/60">
                {t("salaryPayAccount")}
              </span>
              {accountsQuery.isPending ? (
                <Spinner className="h-5 w-5 text-[var(--brand)]" />
              ) : (
                <select
                  required
                  value={accountId}
                  onChange={(event) => setAccountId(event.target.value)}
                  className={SELECT_CLASS}
                >
                  <option value="" />
                  {accounts.map((account) => (
                    <option key={account.id} value={account.id}>
                      {account.name}
                    </option>
                  ))}
                </select>
              )}
            </label>
            {messages.map((message, index) => (
              <p key={index} className="text-sm font-medium text-[var(--danger)]">
                {message}
              </p>
            ))}
            {accountsQuery.isError || errorMessage !== "" ? (
              <p className="text-sm text-[var(--danger)]">
                {errorMessage !== "" ? errorMessage : t("salaryPayError")}
              </p>
            ) : null}
            <Button type="submit" disabled={createPayout.isPending}>
              {createPayout.isPending ? <Spinner className="h-4 w-4" /> : t("salaryPaySubmit")}
            </Button>
          </form>
        </DialogContent>
      </Dialog>
    </>
  );
}
