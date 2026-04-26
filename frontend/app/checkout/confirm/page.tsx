import Link from "next/link";
import { redirect } from "next/navigation";
import { ChevronLeft } from "lucide-react";
import { serverApi } from "@/lib/api/server-api";
import { CheckoutConfirm } from "./CheckoutConfirm";

export const dynamic = "force-dynamic";

export const metadata = { title: "Confirm order" };

export default async function CheckoutConfirmPage() {
  const cart = await serverApi.getCart();
  if (cart.items.length === 0) {
    redirect("/order");
  }

  return (
    <div className="mx-auto max-w-[1100px] px-6 py-8">
      <Link
        href="/checkout"
        className="inline-flex items-center gap-1 text-sm text-[var(--ink)]/60 hover:text-[var(--ink)]"
      >
        <ChevronLeft className="h-4 w-4" />
        Back
      </Link>
      <h1 className="mt-4 font-display text-4xl md:text-5xl">Confirm your order</h1>
      <CheckoutConfirm />
    </div>
  );
}
