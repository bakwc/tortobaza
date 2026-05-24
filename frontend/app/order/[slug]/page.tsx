import Link from "next/link";
import { notFound } from "next/navigation";
import { ChevronLeft } from "lucide-react";
import { getTranslations } from "next-intl/server";
import { serverApi } from "@/lib/api/server-api";
import { ItemDetail } from "@/components/item/ItemDetail";
import { ApiError } from "@/lib/api/client";

export const dynamic = "force-dynamic";

export default async function ItemPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const tCheckout = await getTranslations("checkout");

  let product;
  try {
    product = await serverApi.getProduct(slug);
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) {
      notFound();
    }
    throw e;
  }

  return (
    <div className="mx-auto max-w-[1100px] px-4 py-6">
      <div className="mb-4">
        <Link
          href="/order"
          className="inline-flex items-center gap-1 text-sm text-[var(--ink)]/70 hover:text-[var(--ink)]"
        >
          <ChevronLeft className="h-4 w-4" />
          {tCheckout("backToCatalog")}
        </Link>
      </div>
      <div className="overflow-hidden rounded-3xl bg-white shadow-sm ring-1 ring-[var(--line)]">
        <ItemDetail product={product} variant="page" />
      </div>
    </div>
  );
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  try {
    const product = await serverApi.getProduct(slug);
    return {
      title: product.name,
      description: product.description.slice(0, 160) || product.name,
    };
  } catch {
    const tStatic = await getTranslations("metadata");
    return { title: tStatic("orderTitle") };
  }
}
