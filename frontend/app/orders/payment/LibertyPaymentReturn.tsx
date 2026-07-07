"use client";

import { useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { parseLibertyCustomdata } from "@/lib/liberty-pay";

export function LibertyPaymentReturn({ outcome }: { outcome: "success" | "error" | "cancel" }) {
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    const customdata = searchParams.get("customdata");
    const parsed = parseLibertyCustomdata(customdata);
    if (parsed) {
      router.replace(`/orders/${parsed.number}?token=${parsed.token}&payment=${outcome}`);
      return;
    }
    router.replace("/order");
  }, [outcome, router, searchParams]);

  return <div className="mx-auto max-w-[700px] px-6 py-12 h-48 animate-pulse rounded-3xl bg-white/40" />;
}
