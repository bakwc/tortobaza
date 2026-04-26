import { notFound } from "next/navigation";
import { serverApi } from "@/lib/api/server-api";
import { ItemDialog } from "@/components/item/ItemDialog";
import { ApiError } from "@/lib/api/client";

export const dynamic = "force-dynamic";

export default async function ItemModalPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;

  let product;
  try {
    product = await serverApi.getProduct(slug);
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) {
      notFound();
    }
    throw e;
  }

  return <ItemDialog product={product} />;
}
