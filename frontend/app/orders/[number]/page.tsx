import Link from "next/link";
import { ChevronLeft } from "lucide-react";
import { serverApi } from "@/lib/api/server-api";
import { ApiError } from "@/lib/api/client";
import { OrderStatusView } from "./OrderStatusView";
import { OrderTokenLookup } from "./OrderTokenLookup";

export const dynamic = "force-dynamic";

export const metadata = { title: "Order status" };

export default async function OrderStatusPage({
  params,
  searchParams,
}: {
  params: Promise<{ number: string }>;
  searchParams: Promise<{ token?: string }>;
}) {
  const { number } = await params;
  const { token } = await searchParams;

  if (!token) {
    return (
      <div className="mx-auto max-w-[700px] px-6 py-12">
        <BackToOrder />
        <h1 className="mt-4 font-display text-3xl">Order #{number}</h1>
        <p className="mt-2 text-sm text-[var(--ink)]/60">
          We need a lookup token to display your order details.
        </p>
        <OrderTokenLookup orderNumber={number} />
      </div>
    );
  }

  try {
    const order = await serverApi.getOrder(number, token);
    return (
      <div className="mx-auto max-w-[900px] px-6 py-8">
        <BackToOrder />
        <OrderStatusView order={order} />
      </div>
    );
  } catch (e) {
    const status = e instanceof ApiError ? e.status : 500;
    return (
      <div className="mx-auto max-w-[700px] px-6 py-12">
        <BackToOrder />
        <h1 className="mt-4 font-display text-3xl">Order #{number}</h1>
        <p className="mt-2 text-sm text-[var(--danger)]">
          {status === 404
            ? "We couldn't find this order."
            : "We couldn't load this order. The lookup token may be wrong."}
        </p>
        <OrderTokenLookup orderNumber={number} />
      </div>
    );
  }
}

function BackToOrder() {
  return (
    <Link
      href="/order"
      className="inline-flex items-center gap-1 text-sm text-[var(--ink)]/60 hover:text-[var(--ink)]"
    >
      <ChevronLeft className="h-4 w-4" />
      Back to catalog
    </Link>
  );
}
