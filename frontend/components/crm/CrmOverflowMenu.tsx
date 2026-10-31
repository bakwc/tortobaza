"use client";

import { useState, type ComponentType } from "react";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { BookOpen, ChartColumn, ClipboardList, History, LogOut, MoreHorizontal, Receipt, Users, Wallet, Warehouse } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useCurrentUser, useLogout } from "@/hooks/useAuth";
import { useRsgePendingCount } from "@/hooks/useRsgePendingCount";
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

function PendingBadge({ count }: { count: number }) {
  if (count === 0) return null;
  return (
    <span className="inline-flex min-w-5 animate-pulse items-center justify-center rounded-full bg-red-600 px-1.5 text-xs font-bold text-white">
      {count}
    </span>
  );
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
  const scope = searchParams.get("scope");
  const financeParams = new URLSearchParams();
  if (month) financeParams.set("month", month);
  if (scope === "personal" || scope === "business") financeParams.set("scope", scope);
  const financeQuery = financeParams.toString();
  const financeHref = financeQuery ? `/finance?${financeQuery}` : "/finance";
  const analyticsHref = month ? `/analytics?month=${month}` : "/analytics";
  const isFinanceAdmin = Boolean(currentUser.data?.is_finance_admin);
  const isStaff = Boolean(currentUser.data?.is_staff);
  const pendingQuery = useRsgePendingCount(isFinanceAdmin);
  const pendingCount = pendingQuery.data?.count ?? 0;
  const rsgeHref =
    pendingQuery.data !== undefined && pendingQuery.data.count > 0
      ? pendingQuery.data.section === "invoices"
        ? `/rsge/invoices?month=${pendingQuery.data.month}`
        : `/rsge?month=${pendingQuery.data.month}`
      : "/rsge";

  const items: MenuItem[] = [
    {
      key: "orders",
      href: "/crm",
      label: t("ordersSection"),
      icon: ClipboardList,
      active: isUnder(pathname, "/crm"),
    },
    ...(isFinanceAdmin
      ? [
          {
            key: "analytics",
            href: analyticsHref,
            label: t("analyticsSection"),
            icon: ChartColumn,
            active: isUnder(pathname, "/analytics"),
          },
          {
            key: "finance",
            href: financeHref,
            label: t("finance"),
            icon: Wallet,
            active: isUnder(pathname, "/finance"),
          },
          {
            key: "employees",
            href: "/employees",
            label: t("employeesSection"),
            icon: Users,
            active: isUnder(pathname, "/employees"),
          },
          {
            key: "rsge",
            href: rsgeHref,
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
    ...(isFinanceAdmin
      ? [
          {
            key: "history",
            href: "/history",
            label: t("historySection"),
            icon: History,
            active: isUnder(pathname, "/history"),
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
        className={pendingCount > 0 ? "w-auto gap-1.5 px-2.5" : undefined}
      >
        <MoreHorizontal className="h-4 w-4" />
        <PendingBadge count={pendingCount} />
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
                {item.key === "rsge" && pendingCount > 0 ? (
                  <span className="ml-auto">
                    <PendingBadge count={pendingCount} />
                  </span>
                ) : null}
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
