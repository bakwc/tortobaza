"use client";

import type { ReactNode } from "react";
import { usePathname } from "@/i18n/navigation";

export function SiteChrome({
  header,
  footer,
  children,
}: {
  header: ReactNode;
  footer: ReactNode;
  children: ReactNode;
}) {
  const pathname = usePathname();
  const hideChrome =
    pathname === "/crm" ||
    pathname.startsWith("/crm/") ||
    pathname === "/finance" ||
    pathname.startsWith("/finance/") ||
    pathname === "/menu" ||
    pathname.startsWith("/menu/") ||
    pathname === "/inventory" ||
    pathname.startsWith("/inventory/") ||
    pathname === "/rsge" ||
    pathname.startsWith("/rsge/") ||
    pathname === "/analytics" ||
    pathname.startsWith("/analytics/") ||
    pathname === "/history" ||
    pathname.startsWith("/history/") ||
    pathname === "/employees" ||
    pathname.startsWith("/employees/");

  return (
    <>
      {hideChrome ? null : header}
      <main className="flex-1">{children}</main>
      {hideChrome ? null : footer}
    </>
  );
}
