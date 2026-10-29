"use client";

import type { FormEvent, ReactNode } from "react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { Spinner } from "@/components/ui/spinner";
import { ErrorText } from "@/components/menu/ui";
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
  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    onSubmit();
  };
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
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
        <form className="mt-4 grid gap-4" onSubmit={handleSubmit}>
          {children}
          <ErrorText error={error} />
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
