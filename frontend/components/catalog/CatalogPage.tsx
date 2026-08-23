import { getTranslations } from "next-intl/server";
import { Link } from "@/i18n/navigation";
import { publicApi } from "@/lib/api/public-api";
import { getAllProducts } from "@/lib/api/catalog";
import { CategoryPills } from "@/components/catalog/CategoryPills";
import { CategorySection } from "@/components/catalog/CategorySection";
import { CartSidebar } from "@/components/catalog/CartSidebar";
import { MobileCartBar } from "@/components/catalog/MobileCartBar";

export async function CatalogPage() {
  const [categories, products, landings, t] = await Promise.all([
    publicApi.getCategories(),
    getAllProducts(),
    publicApi.getCategoryLandings(),
    getTranslations("catalog"),
  ]);

  const productsByCategory = new Map<string, typeof products>();
  for (const product of products) {
    const list = productsByCategory.get(product.category.slug) ?? [];
    list.push(product);
    productsByCategory.set(product.category.slug, list);
  }

  const populatedCategories = categories.filter((c) =>
    productsByCategory.has(c.slug),
  );

  const birthdayLanding = landings.find((l) => l.slug === "birthday-cakes");

  return (
    <div className="mx-auto max-w-[1400px] px-6">
      <div className="pt-10 pb-2">
        <h1 className="text-[32px] font-bold leading-[1.05] text-[#666]">
          {t("homeHeading")}
        </h1>
        <p className="mt-4 max-w-3xl text-base leading-relaxed text-[var(--ink)]/75">
          {t("homeIntro")}
        </p>
        {birthdayLanding?.page_slug ? (
          <p className="mt-2 max-w-3xl text-sm leading-relaxed text-[var(--ink)]/70">
            {t("birthdayCakesIntro")}{" "}
            <Link
              href={`/categories/${birthdayLanding.page_slug}`}
              className="underline underline-offset-2 hover:text-[var(--ink)]"
            >
              {t("birthdayCakesLink")}
            </Link>
            .
          </p>
        ) : null}
      </div>

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
