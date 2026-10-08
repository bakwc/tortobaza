"use client";

import type { ReactNode } from "react";
import { useTranslations } from "next-intl";
import { CrmAuthGate } from "@/components/crm/CrmAuthGate";
import { useCurrentUser } from "@/hooks/useAuth";

function FinanceStaffOnly({ children }: { children: ReactNode }) {
  const t = useTranslations("finance");
  const currentUser = useCurrentUser();

  if (!currentUser.data?.is_staff) {
    return (
      <div className="mx-auto max-w-md px-4 py-16 text-center text-sm text-[var(--ink)]">
        {t("staffOnly")}
      </div>
    );
  }

  return children;
}

export function FinanceAuthGate({ children }: { children: ReactNode }) {
  return (
    <CrmAuthGate>
      <FinanceStaffOnly>{children}</FinanceStaffOnly>
    </CrmAuthGate>
  );
}
