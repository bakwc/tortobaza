"use client";

import { useState } from "react";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { Banknote, LogOut, MoreHorizontal, Wallet } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useCurrentUser, useLogout } from "@/hooks/useAuth";
import { Link, usePathname } from "@/i18n/navigation";

export function CrmOverflowMenu() {
  const t = useTranslations("crm");
  const logout = useLogout();
  const currentUser = useCurrentUser();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [open, setOpen] = useState(false);
  const monthParam = searchParams.get("month");
  const dateParam = searchParams.get("date");
  const month = monthParam ?? (dateParam ? dateParam.slice(0, 7) : null);
  const salariesHref = month ? `/crm/salaries?month=${month}` : "/crm/salaries";
  const financeHref = month ? `/finance?month=${month}` : "/finance";
  const showStaffLinks = Boolean(currentUser.data?.is_staff);
  const showSalaries = showStaffLinks && pathname !== "/crm/salaries";

  return (
    <div className="relative">
      <Button
        type="button"
        variant="outline"
        size="icon"
        onClick={() => setOpen((prev) => !prev)}
        aria-label={t("menu")}
        aria-expanded={open}
      >
        <MoreHorizontal className="h-4 w-4" />
      </Button>
      {open ? (
        <div className="absolute right-0 z-20 mt-2 min-w-[180px] rounded-2xl border border-[var(--line)] bg-white py-1 shadow-lg">
          {showSalaries ? (
            <Link
              href={salariesHref}
              className="flex w-full items-center gap-2 px-4 py-2.5 text-left text-sm font-medium text-[var(--ink)] hover:bg-[var(--cream)]"
              onClick={() => setOpen(false)}
            >
              <Banknote className="h-4 w-4" />
              {t("salaries")}
            </Link>
          ) : null}
          {showStaffLinks ? (
            <Link
              href={financeHref}
              className="flex w-full items-center gap-2 px-4 py-2.5 text-left text-sm font-medium text-[var(--ink)] hover:bg-[var(--cream)]"
              onClick={() => setOpen(false)}
            >
              <Wallet className="h-4 w-4" />
              {t("finance")}
            </Link>
          ) : null}
          <button
            type="button"
            className="flex w-full items-center gap-2 px-4 py-2.5 text-left text-sm font-medium text-[var(--ink)] hover:bg-[var(--cream)] disabled:opacity-50"
            onClick={() => {
              setOpen(false);
              logout.mutate(undefined, {
                onSuccess: () => {
                  window.location.reload();
                },
              });
            }}
            disabled={logout.isPending}
          >
            <LogOut className="h-4 w-4" />
            {t("signOut")}
          </button>
        </div>
      ) : null}
    </div>
  );
}
