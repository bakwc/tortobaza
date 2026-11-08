"use client";

import { useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { Spinner } from "@/components/ui/spinner";
import { ErrorText } from "@/components/menu/ui";
import { ApiError } from "@/lib/api/client";
import {
  INVALID_FIELDS_CLASS,
  applyServerErrors,
  clearCustomValidity,
  collectFieldProblems,
  formatFieldProblems,
} from "@/lib/formValidation";
import { cn } from "@/lib/utils";

export function EditorDialog({
  open,
  onOpenChange,
  title,
  pending,
  error,
  onSubmit,
  onCancel,
  onDelete,
  deletePending,
  submitLabel,
  headerAction,
  below,
  children,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  pending: boolean;
  error: unknown;
  onSubmit: () => void;
  onCancel: (() => void) | null;
  onDelete: (() => void) | null;
  deletePending: boolean;
  submitLabel: string | null;
  headerAction: ReactNode | null;
  below: ReactNode;
  children: ReactNode;
}) {
  const t = useTranslations("stock");
  const tForms = useTranslations("forms");
  const formRef = useRef<HTMLFormElement>(null);
  const errorsRef = useRef<HTMLDivElement>(null);
  const [validationShown, setValidationShown] = useState(false);
  const [messages, setMessages] = useState<string[]>([]);
  const [serverMessages, setServerMessages] = useState<string[]>([]);
  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    clearCustomValidity(event.currentTarget);
    const problems = collectFieldProblems(event.currentTarget);
    const next = formatFieldProblems(
      problems,
      (fields) => tForms("requiredFieldsMissing", { fields }),
      (fields) => tForms("invalidFormat", { fields }),
    );
    setValidationShown(true);
    setMessages(next);
    setServerMessages([]);
    if (next.length > 0) return;
    onSubmit();
  };
  useEffect(() => {
    const form = formRef.current;
    if (form === null || !(error instanceof ApiError) || error.status !== 400) {
      setServerMessages([]);
      return;
    }
    setValidationShown(true);
    setServerMessages(
      applyServerErrors(form, error.parsed(), (index) => tForms("rowNumber", { number: index + 1 })),
    );
  }, [error, tForms]);
  useEffect(() => {
    if (serverMessages.length > 0) {
      errorsRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }, [serverMessages]);
  const shown = [...messages, ...serverMessages];
  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next) {
          setValidationShown(false);
          setMessages([]);
          setServerMessages([]);
        }
        onOpenChange(next);
      }}
    >
      <DialogContent className="w-[min(900px,calc(100vw-1.5rem))] overflow-y-auto p-6">
        <DialogTitle
          className={cn(
            "text-lg font-semibold text-[var(--ink)]",
            headerAction ? "pr-28" : "pr-10",
          )}
        >
          {title}
        </DialogTitle>
        <DialogDescription className="hidden">{title}</DialogDescription>
        {headerAction ? <div className="absolute right-16 top-4 z-10">{headerAction}</div> : null}
        <form
          ref={formRef}
          noValidate
          data-validated={validationShown ? "" : undefined}
          className={cn("mt-4 grid gap-4", INVALID_FIELDS_CLASS)}
          onSubmit={handleSubmit}
          onInput={(event) => {
            const target = event.target;
            if (
              target instanceof HTMLInputElement ||
              target instanceof HTMLTextAreaElement ||
              target instanceof HTMLSelectElement
            ) {
              target.setCustomValidity("");
            }
          }}
        >
          {children}
          {shown.length > 0 ? (
            <div ref={errorsRef} data-form-errors className="grid gap-1">
              {shown.map((message, index) => (
                <p key={index} className="text-sm font-medium text-[var(--danger)]">
                  {message}
                </p>
              ))}
            </div>
          ) : null}
          {error instanceof ApiError && error.status === 400 ? null : <ErrorText error={error} />}
          <div className="flex flex-wrap justify-between gap-3">
            {onDelete ? (
              <Button type="button" variant="outline" onClick={onDelete} disabled={deletePending}>
                {deletePending ? <Spinner className="h-4 w-4" /> : t("delete")}
              </Button>
            ) : (
              <span />
            )}
            <div className="flex gap-2">
              {onCancel !== null ? (
                <Button type="button" variant="outline" onClick={onCancel}>
                  {t("cancel")}
                </Button>
              ) : null}
              {submitLabel !== null ? (
                <Button type="submit" disabled={pending}>
                  {pending ? <Spinner className="h-4 w-4" /> : submitLabel}
                </Button>
              ) : null}
            </div>
          </div>
        </form>
        {below === null ? null : <div className="mt-6 border-t border-[var(--line)] pt-5">{below}</div>}
      </DialogContent>
    </Dialog>
  );
}
