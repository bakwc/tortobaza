import { notFound } from "next/navigation";
import { setRequestLocale } from "next-intl/server";
import { ItemDialog } from "@/components/item/ItemDialog";
import { ApiError } from "@/lib/api/client";
import { publicApi } from "@/lib/api/public-api";

export const revalidate = 300;

export default async function ItemModalPage({
  params,
}: {
  params: Promise<{ locale: string; slug: string }>;
}) {
  const { locale, slug } = await params;
  setRequestLocale(locale);

  let product;
  try {
    product = await publicApi.getProduct(slug);
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) {
      notFound();
    }
    throw e;
  }

  return <ItemDialog product={product} />;
}
