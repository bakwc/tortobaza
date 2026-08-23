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
  const hideChrome = pathname === "/crm" || pathname.startsWith("/crm/");

  return (
    <>
      {hideChrome ? null : header}
      <main className="flex-1">{children}</main>
      {hideChrome ? null : footer}
    </>
  );
}
