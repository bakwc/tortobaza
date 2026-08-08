import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { publicApi } from "@/lib/api/public-api";
import { getAllProducts } from "@/lib/api/catalog";
import { CategoryPills } from "@/components/catalog/CategoryPills";
import { CategorySection } from "@/components/catalog/CategorySection";
import { CartSidebar } from "@/components/catalog/CartSidebar";
import { MobileCartBar } from "@/components/catalog/MobileCartBar";
import type { Locale } from "@/i18n/routing";
import { routing } from "@/i18n/routing";
import { languageAlternates, localePath } from "@/lib/seo";
import { getPublicSiteOrigin } from "@/lib/site-origin";

export const revalidate = 300;

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale } = await params;
  setRequestLocale(locale);
  const [t, origin] = await Promise.all([
    getTranslations("metadata"),
    getPublicSiteOrigin(),
  ]);
  const pathsByLocale = Object.fromEntries(
    routing.locales.map((loc) => [loc, "/order"]),
  ) as Record<Locale, string>;
  const path = localePath(locale as Locale, "/order");
  return {
    title: t("orderTitle"),
    description: t("orderDescription"),
    alternates: {
      canonical: path,
      ...languageAlternates(origin, pathsByLocale),
    },
    openGraph: {
      title: t("orderTitle"),
      description: t("orderDescription"),
      url: path,
    },
  };
}

export default async function OrderPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);

  const [categories, products] = await Promise.all([
    publicApi.getCategories(),
    getAllProducts(),
  ]);

  const productsByCategory = new Map<string, typeof products>();
  for (const product of products) {
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
