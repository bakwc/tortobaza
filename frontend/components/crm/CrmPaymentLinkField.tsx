"use client";

import { useEffect, useState } from "react";
import { Check, Copy } from "lucide-react";
import { useTranslations } from "next-intl";
import { apiErrorMessage } from "@/components/menu/ui";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { useCreateCrmPaymentLink } from "@/hooks/useCrmOrders";

export function CrmPaymentLinkField({
  orderId,
  paymentUrl,
  remaining,
}: {
  orderId: number;
  paymentUrl: string | null;
  remaining: number;
}) {
  const t = useTranslations("crm");
  const createLink = useCreateCrmPaymentLink();
  const [copied, setCopied] = useState(false);
  const createdUrl = createLink.data ? createLink.data.payment_url : null;
  const url = paymentUrl ?? createdUrl;

  useEffect(() => {
    if (!copied) return;
    const timer = window.setTimeout(() => setCopied(false), 2000);
    return () => window.clearTimeout(timer);
  }, [copied]);

  if (url === null && remaining <= 0) {
    return null;
  }

  const copy = () => {
    if (url === null) return;
    void navigator.clipboard.writeText(url);
    setCopied(true);
  };

  return (
    <div className="flex flex-col gap-1.5">
      <span className="text-xs font-medium uppercase tracking-wide text-[var(--ink)]/60">
        {t("paymentPage")}
      </span>
      {url !== null ? (
        <div className="flex gap-2">
          <Input readOnly value={url} className="min-w-0 flex-1" />
          <Button type="button" variant="outline" className="h-12 shrink-0 px-5" onClick={copy}>
            {copied ? <Check className="mr-1.5 h-4 w-4" /> : <Copy className="mr-1.5 h-4 w-4" />}
            {copied ? t("paymentLinkCopied") : t("copyPaymentLink")}
          </Button>
        </div>
      ) : (
        <Button
          type="button"
          variant="outline"
          className="h-12 w-fit px-5"
          disabled={createLink.isPending}
          onClick={() => createLink.mutate(orderId)}
        >
          {createLink.isPending ? <Spinner className="mr-1.5 h-4 w-4" /> : null}
          {t("createPaymentLink")}
        </Button>
      )}
      {createLink.isError ? (
        <p className="text-sm text-[var(--danger)]">
          {apiErrorMessage(createLink.error, t("genericError"))}
        </p>
      ) : null}
    </div>
  );
}
