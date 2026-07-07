import Link from "next/link";
import { ChevronLeft } from "lucide-react";
import { getTranslations } from "next-intl/server";
import { serverApi } from "@/lib/api/server-api";
import { ApiError } from "@/lib/api/client";
import { OrderStatusView } from "./OrderStatusView";
import { OrderTokenLookup } from "./OrderTokenLookup";

export const dynamic = "force-dynamic";

export async function generateMetadata() {
  const t = await getTranslations("metadata");
  return {
    title: t("orderStatusTitle"),
    description: t("rootDescription"),
  };
}

export default async function OrderStatusPage({
  params,
  searchParams,
}: {
  params: Promise<{ number: string }>;
  searchParams: Promise<{ token?: string; payment?: string }>;
}) {
  const tOrders = await getTranslations("orders");
  const tCheckout = await getTranslations("checkout");
  const { number } = await params;
  const { token, payment } = await searchParams;
  const paymentResult =
    payment === "success" || payment === "error" || payment === "cancel" ? payment : null;

  if (!token) {
    return (
      <div className="mx-auto max-w-[700px] px-6 py-12">
        <Link
          href="/order"
          className="inline-flex items-center gap-1 text-sm text-[var(--ink)]/60 hover:text-[var(--ink)]"
        >
          <ChevronLeft className="h-4 w-4" />
          {tCheckout("backToCatalog")}
        </Link>
        <h1 className="mt-4 font-display text-3xl">#{number}</h1>
        <p className="mt-2 text-sm text-[var(--ink)]/60">{tOrders("lookupNeedToken")}</p>
        <OrderTokenLookup orderNumber={number} />
      </div>
    );
  }

  try {
    const order = await serverApi.getOrder(number, token);
    return (
      <div className="mx-auto max-w-[900px] px-6 py-8">
        <Link
          href="/order"
          className="inline-flex items-center gap-1 text-sm text-[var(--ink)]/60 hover:text-[var(--ink)]"
        >
          <ChevronLeft className="h-4 w-4" />
          {tCheckout("backToCatalog")}
        </Link>
        <OrderStatusView order={order} paymentResult={paymentResult} />
      </div>
    );
  } catch (e) {
    const status = e instanceof ApiError ? e.status : 500;
    return (
      <div className="mx-auto max-w-[700px] px-6 py-12">
        <Link
          href="/order"
          className="inline-flex items-center gap-1 text-sm text-[var(--ink)]/60 hover:text-[var(--ink)]"
        >
          <ChevronLeft className="h-4 w-4" />
          {tCheckout("backToCatalog")}
        </Link>
        <h1 className="mt-4 font-display text-3xl">#{number}</h1>
        <p className="mt-2 text-sm text-[var(--danger)]">
          {status === 404 ? tOrders("notFound404") : tOrders("loadFail")}
        </p>
        <OrderTokenLookup orderNumber={number} />
      </div>
    );
  }
}
