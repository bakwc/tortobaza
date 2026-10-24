"use client";

import { useState, type ComponentType } from "react";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { Banknote, BookOpen, ClipboardList, LogOut, MoreHorizontal, Receipt, Wallet, Warehouse } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useCurrentUser, useLogout } from "@/hooks/useAuth";
import { Link, usePathname } from "@/i18n/navigation";

type MenuItem = {
  key: string;
  href: string;
  label: string;
  icon: ComponentType<{ className?: string }>;
  active: boolean;
};

function isUnder(pathname: string, base: string): boolean {
  return pathname === base || pathname.startsWith(`${base}/`);
}

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
  const isFinanceAdmin = Boolean(currentUser.data?.is_finance_admin);
  const isStaff = Boolean(currentUser.data?.is_staff);
  const isSalaries = isUnder(pathname, "/crm/salaries");

  const items: MenuItem[] = [
    {
      key: "orders",
      href: "/crm",
      label: t("ordersSection"),
      icon: ClipboardList,
      active: isUnder(pathname, "/crm") && !isSalaries,
    },
    ...(isFinanceAdmin
      ? [
          {
            key: "finance",
            href: financeHref,
            label: t("finance"),
            icon: Wallet,
            active: isUnder(pathname, "/finance"),
          },
          {
            key: "salaries",
            href: salariesHref,
            label: t("salaries"),
            icon: Banknote,
            active: isSalaries,
          },
          {
            key: "rsge",
            href: "/rsge",
            label: t("rsgeSection"),
            icon: Receipt,
            active: isUnder(pathname, "/rsge"),
          },
        ]
      : []),
    ...(isStaff
      ? [
          {
            key: "menu",
            href: "/menu",
            label: t("menuSection"),
            icon: BookOpen,
            active: isUnder(pathname, "/menu"),
          },
          {
            key: "inventory",
            href: "/inventory",
            label: t("inventorySection"),
            icon: Warehouse,
            active: isUnder(pathname, "/inventory"),
          },
        ]
      : []),
  ];

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
          {items.map((item) => {
            const Icon = item.icon;
            return (
              <Link
                key={item.key}
                href={item.href}
                aria-current={item.active ? "page" : undefined}
                className={`flex w-full items-center gap-2 px-4 py-2.5 text-left text-sm font-medium text-[var(--ink)] ${
                  item.active ? "bg-[var(--brand)]/15" : "hover:bg-[var(--cream)]"
                }`}
                onClick={() => setOpen(false)}
              >
                <Icon className="h-4 w-4" />
                {item.label}
              </Link>
            );
          })}
          <div className="my-1 border-t border-[var(--line)]" />
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
