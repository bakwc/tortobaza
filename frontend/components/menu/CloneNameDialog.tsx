"use client";

import { useState, type FormEvent } from "react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { ErrorText, Field } from "@/components/menu/ui";

export function CloneNameDialog({
  name,
  pending,
  error,
  onOpenChange,
  onSubmit,
}: {
  name: string;
  pending: boolean;
  error: unknown;
  onOpenChange: (open: boolean) => void;
  onSubmit: (name: string) => void;
}) {
  const t = useTranslations("stock");
  const [value, setValue] = useState(name);
  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const next = value.trim();
    if (next === "") return;
    onSubmit(next);
  };
  return (
    <Dialog open onOpenChange={onOpenChange}>
      <DialogContent className="w-[min(420px,calc(100vw-1.5rem))] p-6">
        <DialogTitle className="text-lg font-semibold text-[var(--ink)]">{t("clone")}</DialogTitle>
        <DialogDescription className="hidden">{t("cloneName")}</DialogDescription>
        <form className="mt-4 grid gap-4" onSubmit={submit}>
          <Field label={t("cloneName")}>
            <Input required autoFocus value={value} onChange={(event) => setValue(event.target.value)} />
          </Field>
          <ErrorText error={error} />
          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              {t("cancel")}
            </Button>
            <Button type="submit" disabled={pending}>
              {t("clone")}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
