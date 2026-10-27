"use client";

import { useSearchParams } from "next/navigation";
import { usePathname, useRouter } from "@/i18n/navigation";
import type { FinanceScope } from "@/lib/api/endpoints";

export function useFinanceScope(): {
  scope: FinanceScope;
  setScope: (next: FinanceScope) => void;
} {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const scope: FinanceScope = searchParams.get("scope") === "personal" ? "personal" : "business";

  const setScope = (next: FinanceScope) => {
    const params = new URLSearchParams(searchParams.toString());
    params.set("scope", next);
    router.replace(`${pathname}?${params.toString()}`);
  };

  return { scope, setScope };
}
