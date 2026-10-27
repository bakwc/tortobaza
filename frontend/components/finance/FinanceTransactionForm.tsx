"use client";

import { useState, type FormEvent } from "react";
import { useLocale, useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Spinner } from "@/components/ui/spinner";
import { Textarea } from "@/components/ui/textarea";
import { useFinanceScope } from "@/hooks/useFinanceScope";
import {
  useCreateFinanceTransaction,
  useDeleteFinanceTransaction,
  useFinanceAccounts,
  useFinanceTransactionSearch,
  useUpdateFinanceTransaction,
} from "@/hooks/useFinanceTransactions";
import { ApiError } from "@/lib/api/client";
import type {
  FinanceTransaction,
  FinanceTransactionSearchResult,
  FinanceTransactionWriteBody,
} from "@/lib/api/types";
import { formatCrmDate, formatMoney, getTbilisiTodayIsoDate } from "@/lib/format";
import { cn } from "@/lib/utils";

const KINDS: FinanceTransaction["kind"][] = [
  "income",
  "expense",
  "transfer",
  "withdrawal",
  "investment",
  "correction",
  "other",
];

const INCOME_TYPES = ["online", "terminal", "cash", "transfer"] as const;
const EXPENSE_TYPES = [
  "salary",
  "rent",
  "products",
  "consumables",
  "equipment",
  "fees",
  "taxi",
  "gasoline",
  "marketing",
  "training",
] as const;

const PAIR_MODES = ["none", "link", "create"] as const;

type PairMode = (typeof PAIR_MODES)[number];

type Fields = {
  date: string;
  accountId: string;
  amount: string;
  kind: FinanceTransaction["kind"];
  incomeType: string;
  expenseType: string;
  counterpartyName: string;
  counterpartyIban: string;
  description: string;
  transferPair: PairMode;
  matchedTransactionId: number | null;
  counterpartAccountId: string;
  counterpartDate: string;
  counterpartAmount: string;
};

const SELECT_CLASS =
  "h-12 w-full rounded-full border border-[var(--line)] bg-white px-5 text-sm text-[var(--ink)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--brand)]/30";

function negatedAmount(amount: string): string {
  if (amount.trim() === "") return "";
  const value = Number(amount);
  if (!Number.isFinite(value)) return "";
  return (-value).toFixed(2);
}

function initialFields(transaction: FinanceTransaction | null): Fields {
  const today = getTbilisiTodayIsoDate();
  if (transaction === null) {
    return {
      date: today,
      accountId: "",
      amount: "",
      kind: "expense",
      incomeType: "",
      expenseType: "",
      counterpartyName: "",
      counterpartyIban: "",
      description: "",
      transferPair: "none",
      matchedTransactionId: null,
      counterpartAccountId: "",
      counterpartDate: today,
      counterpartAmount: "",
    };
  }
  const matched = transaction.kind === "transfer" ? transaction.matched_transaction : null;
  return {
    date: transaction.date,
    accountId: String(transaction.account.id),
    amount: transaction.amount,
    kind: transaction.kind,
    incomeType: transaction.income_type,
    expenseType: transaction.expense_type,
    counterpartyName: transaction.counterparty_name,
    counterpartyIban: transaction.counterparty_iban,
    description: transaction.description,
    transferPair: matched === null ? "none" : "link",
    matchedTransactionId: matched === null ? null : matched.id,
    counterpartAccountId: "",
    counterpartDate: transaction.date,
    counterpartAmount: negatedAmount(transaction.amount),
  };
}

function buildBody(fields: Fields): FinanceTransactionWriteBody {
  const transfer = fields.kind === "transfer";
  return {
    date: fields.date,
    account_id: Number(fields.accountId),
    amount: fields.amount,
    kind: fields.kind,
    income_type: fields.kind === "income" ? fields.incomeType : "",
    expense_type: fields.kind === "expense" ? fields.expenseType : "",
    counterparty_name: fields.counterpartyName,
    counterparty_iban: fields.counterpartyIban,
    description: fields.description,
    transfer_pair: transfer ? fields.transferPair : "none",
    matched_transaction_id:
      transfer && fields.transferPair === "link" ? fields.matchedTransactionId : null,
    counterpart:
      transfer && fields.transferPair === "create"
        ? {
            account_id: Number(fields.counterpartAccountId),
            date: fields.counterpartDate,
            amount: fields.counterpartAmount,
          }
        : null,
  };
}

export function FinanceTransactionForm({
  open,
  transaction,
  onClose,
}: {
  open: boolean;
  transaction: FinanceTransaction | null;
  onClose: () => void;
}) {
  const t = useTranslations("finance");
  const locale = useLocale();
  const { scope } = useFinanceScope();
  const accountsQuery = useFinanceAccounts(open, scope);
  const [fields, setFields] = useState<Fields>(() => initialFields(transaction));
  const [selectedMatch, setSelectedMatch] = useState<FinanceTransactionSearchResult | null>(() =>
    transaction !== null && transaction.kind === "transfer" ? transaction.matched_transaction : null,
  );
  const [searchInput, setSearchInput] = useState("");
  const [submittedQuery, setSubmittedQuery] = useState("");
  const [counterpartTouched, setCounterpartTouched] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const searchQuery = useFinanceTransactionSearch(submittedQuery, scope);
  const createMutation = useCreateFinanceTransaction(scope);
  const updateMutation = useUpdateFinanceTransaction(scope);
  const deleteMutation = useDeleteFinanceTransaction(scope);
  const pending = createMutation.isPending || updateMutation.isPending || deleteMutation.isPending;

  function setKind(kind: FinanceTransaction["kind"]) {
    setFields((current) => ({
      ...current,
      kind,
      incomeType: kind === "income" ? current.incomeType : "",
      expenseType: kind === "expense" ? current.expenseType : "",
      transferPair: kind === "transfer" ? current.transferPair : "none",
    }));
  }

  function setTransferPair(pair: PairMode) {
    setCounterpartTouched(false);
    setFields((current) => {
      if (pair !== "create") return { ...current, transferPair: pair };
      return {
        ...current,
        transferPair: pair,
        counterpartDate: current.date,
        counterpartAmount: negatedAmount(current.amount),
      };
    });
  }

  function setDate(date: string) {
    setFields((current) => ({
      ...current,
      date,
      counterpartDate:
        current.transferPair === "create" && !counterpartTouched ? date : current.counterpartDate,
    }));
  }

  function setAmount(amount: string) {
    setFields((current) => ({
      ...current,
      amount,
      counterpartAmount:
        current.transferPair === "create" && !counterpartTouched
          ? negatedAmount(amount)
          : current.counterpartAmount,
    }));
  }

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrorMessage("");
    if (
      fields.kind === "transfer" &&
      fields.transferPair === "link" &&
      fields.matchedTransactionId === null
    ) {
      setErrorMessage(t("form.chooseMatch"));
      return;
    }
    const body = buildBody(fields);
    if (transaction === null) {
      createMutation.mutate(body, { onSuccess: onClose, onError });
      return;
    }
    updateMutation.mutate({ id: transaction.id, body }, { onSuccess: onClose, onError });
  }

  function onError(error: unknown) {
    if (error instanceof ApiError) {
      setErrorMessage(error.detail);
      return;
    }
    throw error;
  }

  function onDelete() {
    if (transaction === null) return;
    setErrorMessage("");
    deleteMutation.mutate(transaction.id, { onSuccess: onClose, onError });
  }

  const accounts = accountsQuery.data ?? [];
  const searchResults = (searchQuery.data ?? []).filter((item) => item.id !== transaction?.id);

  return (
    <Dialog open={open} onOpenChange={(next) => (next ? undefined : onClose())}>
      <DialogContent className="w-[min(560px,calc(100vw-1.5rem))] overflow-y-auto">
        <form className="grid gap-4 px-5 pb-6 pt-5" onSubmit={onSubmit}>
          <div className="pr-12">
            <DialogTitle className="text-lg font-semibold text-[var(--ink)]">
              {transaction === null ? t("form.createTitle") : t("form.editTitle")}
            </DialogTitle>
            <DialogDescription className="sr-only">
              {transaction === null ? t("form.createTitle") : t("form.editTitle")}
            </DialogDescription>
          </div>

          {accountsQuery.isError ? (
            <p className="text-sm text-[var(--danger)]">{t("loadError")}</p>
          ) : accountsQuery.isPending ? (
            <div className="flex min-h-40 items-center justify-center">
              <Spinner className="h-6 w-6 text-[var(--brand)]" />
            </div>
          ) : (
            <div className="grid gap-4">
              <label className="flex flex-col gap-1.5">
                <span className="text-xs font-medium uppercase tracking-wide text-[var(--ink)]/60">
                  {t("form.date")}
                </span>
                <Input required type="date" value={fields.date} onChange={(event) => setDate(event.target.value)} />
              </label>
              <label className="flex flex-col gap-1.5">
                <span className="text-xs font-medium uppercase tracking-wide text-[var(--ink)]/60">
                  {t("form.account")}
                </span>
                <select
                  required
                  value={fields.accountId}
                  onChange={(event) => {
                    const accountId = event.target.value;
                    setFields((current) => ({
                      ...current,
                      accountId,
                      counterpartAccountId:
                        current.counterpartAccountId === accountId ? "" : current.counterpartAccountId,
                    }));
                  }}
                  className={SELECT_CLASS}
                >
                  <option value="">{t("form.chooseAccount")}</option>
                  {accounts.map((account) => (
                    <option key={account.id} value={account.id}>
                      {account.name} ({account.currency})
                    </option>
                  ))}
                </select>
              </label>
              <label className="flex flex-col gap-1.5">
                <span className="text-xs font-medium uppercase tracking-wide text-[var(--ink)]/60">
                  {t("form.amount")}
                </span>
                <Input
                  required
                  inputMode="decimal"
                  value={fields.amount}
                  onChange={(event) => setAmount(event.target.value)}
                />
              </label>
              <label className="flex flex-col gap-1.5">
                <span className="text-xs font-medium uppercase tracking-wide text-[var(--ink)]/60">
                  {t("form.kind")}
                </span>
                <select
                  required
                  value={fields.kind}
                  onChange={(event) => setKind(event.target.value as FinanceTransaction["kind"])}
                  className={SELECT_CLASS}
                >
                  {KINDS.map((kind) => (
                    <option key={kind} value={kind}>
                      {t(`kinds.${kind}`)}
                    </option>
                  ))}
                </select>
              </label>
              {fields.kind === "income" ? (
                <label className="flex flex-col gap-1.5">
                  <span className="text-xs font-medium uppercase tracking-wide text-[var(--ink)]/60">
                    {t("form.incomeType")}
                  </span>
                  <select
                    value={fields.incomeType}
                    onChange={(event) => setFields((current) => ({ ...current, incomeType: event.target.value }))}
                    className={SELECT_CLASS}
                  >
                    <option value="">{t("unspecified")}</option>
                    {INCOME_TYPES.map((type) => (
                      <option key={type} value={type}>
                        {t(`incomeTypes.${type}`)}
                      </option>
                    ))}
                  </select>
                </label>
              ) : null}
              {fields.kind === "expense" ? (
                <label className="flex flex-col gap-1.5">
                  <span className="text-xs font-medium uppercase tracking-wide text-[var(--ink)]/60">
                    {t("form.expenseType")}
                  </span>
                  <select
                    value={fields.expenseType}
                    onChange={(event) =>
                      setFields((current) => ({ ...current, expenseType: event.target.value }))
                    }
                    className={SELECT_CLASS}
                  >
                    <option value="">{t("unspecified")}</option>
                    {EXPENSE_TYPES.map((type) => (
                      <option key={type} value={type}>
                        {t(`expenseTypes.${type}`)}
                      </option>
                    ))}
                  </select>
                </label>
              ) : null}
              <label className="flex flex-col gap-1.5">
                <span className="text-xs font-medium uppercase tracking-wide text-[var(--ink)]/60">
                  {t("form.counterparty")}
                </span>
                <Input
                  value={fields.counterpartyName}
                  onChange={(event) =>
                    setFields((current) => ({ ...current, counterpartyName: event.target.value }))
                  }
                />
              </label>
              <label className="flex flex-col gap-1.5">
                <span className="text-xs font-medium uppercase tracking-wide text-[var(--ink)]/60">
                  {t("form.counterpartyIban")}
                </span>
                <Input
                  value={fields.counterpartyIban}
                  onChange={(event) =>
                    setFields((current) => ({ ...current, counterpartyIban: event.target.value }))
                  }
                />
              </label>
              <label className="flex flex-col gap-1.5">
                <span className="text-xs font-medium uppercase tracking-wide text-[var(--ink)]/60">
                  {t("form.description")}
                </span>
                <Textarea
                  value={fields.description}
                  onChange={(event) =>
                    setFields((current) => ({ ...current, description: event.target.value }))
                  }
                />
              </label>

              {fields.kind === "transfer" ? (
                <div className="grid gap-3">
                  <span className="text-xs font-medium uppercase tracking-wide text-[var(--ink)]/60">
                    {t("form.pair")}
                  </span>
                  <RadioGroup
                    value={fields.transferPair}
                    onValueChange={(value) => setTransferPair(value as PairMode)}
                    className="grid gap-2"
                  >
                    {PAIR_MODES.map((mode) => (
                      <label
                        key={mode}
                        className={cn(
                          "flex cursor-pointer items-center gap-2 rounded-2xl border px-3 py-3 text-sm",
                          fields.transferPair === mode
                            ? "border-[var(--brand)] bg-[var(--cream)]"
                            : "border-[var(--line)]",
                        )}
                      >
                        <RadioGroupItem value={mode} />
                        {t(`form.pairModes.${mode}`)}
                      </label>
                    ))}
                  </RadioGroup>

                  {fields.transferPair === "link" ? (
                    <div className="grid gap-2">
                      {selectedMatch ? (
                        <MatchCard match={selectedMatch} locale={locale} />
                      ) : (
                        <span className="text-sm text-[var(--muted-2)]">{t("form.chooseMatch")}</span>
                      )}
                      <div className="flex gap-2">
                        <Input
                          value={searchInput}
                          placeholder={t("form.pairSearchPlaceholder")}
                          onChange={(event) => setSearchInput(event.target.value)}
                          onKeyDown={(event) => {
                            if (event.key !== "Enter") return;
                            event.preventDefault();
                            setSubmittedQuery(searchInput.trim());
                          }}
                        />
                        <Button
                          type="button"
                          variant="outline"
                          onClick={() => setSubmittedQuery(searchInput.trim())}
                        >
                          {t("form.pairSearch")}
                        </Button>
                      </div>
                      {submittedQuery !== "" && searchQuery.isPending ? (
                        <Spinner className="h-5 w-5 text-[var(--brand)]" />
                      ) : null}
                      {submittedQuery !== "" && searchQuery.isError ? (
                        <p className="text-sm text-[var(--danger)]">{t("loadError")}</p>
                      ) : null}
                      {submittedQuery !== "" && searchQuery.data && searchResults.length === 0 ? (
                        <p className="text-sm text-[var(--muted-2)]">{t("form.noSearchResults")}</p>
                      ) : null}
                      {submittedQuery !== ""
                        ? searchResults.map((item) => (
                            <button
                              key={item.id}
                              type="button"
                              onClick={() => {
                                setSelectedMatch(item);
                                setFields((current) => ({ ...current, matchedTransactionId: item.id }));
                              }}
                              className={cn(
                                "rounded-xl border px-3 py-2 text-left",
                                selectedMatch?.id === item.id
                                  ? "border-[var(--brand)] bg-[var(--cream)]"
                                  : "border-[var(--line)] bg-white",
                              )}
                            >
                              <MatchCard match={item} locale={locale} />
                            </button>
                          ))
                        : null}
                    </div>
                  ) : null}

                  {fields.transferPair === "create" ? (
                    <div className="grid gap-4">
                      <label className="flex flex-col gap-1.5">
                        <span className="text-xs font-medium uppercase tracking-wide text-[var(--ink)]/60">
                          {t("form.counterpartAccount")}
                        </span>
                        <select
                          required
                          value={fields.counterpartAccountId}
                          onChange={(event) =>
                            setFields((current) => ({
                              ...current,
                              counterpartAccountId: event.target.value,
                            }))
                          }
                          className={SELECT_CLASS}
                        >
                          <option value="">{t("form.chooseAccount")}</option>
                          {accounts
                            .filter((account) => String(account.id) !== fields.accountId)
                            .map((account) => (
                              <option key={account.id} value={account.id}>
                                {account.name} ({account.currency})
                              </option>
                            ))}
                        </select>
                      </label>
                      <label className="flex flex-col gap-1.5">
                        <span className="text-xs font-medium uppercase tracking-wide text-[var(--ink)]/60">
                          {t("form.counterpartDate")}
                        </span>
                        <Input
                          required
                          type="date"
                          value={fields.counterpartDate}
                          onChange={(event) => {
                            setCounterpartTouched(true);
                            setFields((current) => ({
                              ...current,
                              counterpartDate: event.target.value,
                            }));
                          }}
                        />
                      </label>
                      <label className="flex flex-col gap-1.5">
                        <span className="text-xs font-medium uppercase tracking-wide text-[var(--ink)]/60">
                          {t("form.counterpartAmount")}
                        </span>
                        <Input
                          required
                          inputMode="decimal"
                          value={fields.counterpartAmount}
                          onChange={(event) => {
                            setCounterpartTouched(true);
                            setFields((current) => ({
                              ...current,
                              counterpartAmount: event.target.value,
                            }));
                          }}
                        />
                      </label>
                    </div>
                  ) : null}
                </div>
              ) : null}
            </div>
          )}

          {errorMessage ? <p className="text-sm text-[var(--danger)]">{errorMessage}</p> : null}

          <div className="flex flex-wrap justify-between gap-3">
            {transaction !== null ? (
              <Button type="button" variant="outline" onClick={onDelete} disabled={pending}>
                {deleteMutation.isPending ? <Spinner className="h-4 w-4" /> : t("form.delete")}
              </Button>
            ) : (
              <span />
            )}
            <Button type="submit" disabled={pending || accountsQuery.isPending || accountsQuery.isError}>
              {createMutation.isPending || updateMutation.isPending ? (
                <Spinner className="h-4 w-4" />
              ) : (
                t("form.save")
              )}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function MatchCard({ match, locale }: { match: FinanceTransactionSearchResult; locale: string }) {
  const title = match.counterparty_name || match.description || `#${match.id}`;
  return (
    <div className="grid gap-0.5 text-sm">
      <div className="flex items-baseline justify-between gap-2">
        <span className="min-w-0 truncate font-semibold text-[var(--ink)]">{title}</span>
        <span className="shrink-0 font-bold text-[var(--ink)]">
          {formatMoney(match.amount, match.account.currency)}
        </span>
      </div>
      <span className="text-xs text-[var(--muted-2)]">
        {formatCrmDate(match.date, locale)} · {match.account.name} · #{match.id}
      </span>
      {match.description && match.counterparty_name ? (
        <span className="whitespace-pre-wrap break-words text-xs text-[var(--muted-2)]">{match.description}</span>
      ) : null}
    </div>
  );
}
