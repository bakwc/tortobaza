import { getTranslations } from "next-intl/server";
import { serverApi } from "@/lib/api/server-api";
import { CategoryPills } from "@/components/catalog/CategoryPills";
import { CategorySection } from "@/components/catalog/CategorySection";
import { CartSidebar } from "@/components/catalog/CartSidebar";
import { MobileCartBar } from "@/components/catalog/MobileCartBar";

export const dynamic = "force-dynamic";

export async function generateMetadata() {
  const t = await getTranslations("metadata");
  return {
    title: t("orderTitle"),
    description: t("orderDescription"),
  };
}

export default async function OrderPage() {
  const [categories, productsPage] = await Promise.all([
    serverApi.getCategories(),
    serverApi.getProducts({ page_size: 200 }),
  ]);

  const productsByCategory = new Map<string, typeof productsPage.results>();
  for (const product of productsPage.results) {
    const list = productsByCategory.get(product.category.slug) ?? [];
    list.push(product);
    productsByCategory.set(product.category.slug, list);
  }

  const populatedCategories = categories.filter((c) => productsByCategory.has(c.slug));

  return (
    <div className="mx-auto max-w-[1400px] px-6">
      <CategoryPills categories={populatedCategories} />

      <div className="grid gap-8 pb-32 lg:grid-cols-[1fr_360px] lg:gap-10 lg:pb-20">
        <div>
          {populatedCategories.map((category) => (
            <CategorySection
              key={category.id}
              category={category}
              products={productsByCategory.get(category.slug) ?? []}
            />
          ))}
        </div>
        <div className="hidden lg:block">
          <CartSidebar />
        </div>
      </div>

      <div className="fixed inset-x-0 bottom-0 z-30 px-4 pb-4 lg:hidden">
        <MobileCartBar />
      </div>
    </div>
  );
}
