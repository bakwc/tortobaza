import Link from "next/link";
import { redirect } from "next/navigation";
import { ChevronLeft } from "lucide-react";
import { getTranslations } from "next-intl/server";
import { serverApi } from "@/lib/api/server-api";
import { CheckoutPageClient } from "./CheckoutPageClient";

export const dynamic = "force-dynamic";

export async function generateMetadata() {
  const t = await getTranslations("metadata");
  return {
    title: t("checkoutTitle"),
    description: t("checkoutDescription"),
  };
}

export default async function CheckoutPage() {
  const tCheckout = await getTranslations("checkout");
  const cart = await serverApi.getCart();
  if (cart.items.length === 0) {
    redirect("/order");
  }

  return (
    <div className="mx-auto max-w-[1100px] px-6 py-8">
      <Link
        href="/order"
        className="inline-flex items-center gap-1 text-sm text-[var(--ink)]/60 hover:text-[var(--ink)]"
      >
        <ChevronLeft className="h-4 w-4" />
        {tCheckout("backToCatalog")}
      </Link>

      <h1 className="mt-4 font-display text-4xl md:text-5xl">{tCheckout("yourDelivery")}</h1>

      <CheckoutPageClient />
    </div>
  );
}
