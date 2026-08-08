import { Suspense } from "react";
import { LibertyPaymentReturn } from "../LibertyPaymentReturn";

export default function LibertyPaymentSuccessPage() {
  return (
    <Suspense fallback={<div className="mx-auto max-w-[700px] px-6 py-12 h-48 animate-pulse rounded-3xl bg-white/40" />}>
      <LibertyPaymentReturn outcome="success" />
    </Suspense>
  );
}
