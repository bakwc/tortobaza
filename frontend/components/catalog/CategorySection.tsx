import { getTranslations } from "next-intl/server";
import { ProductCard } from "./ProductCard";
import type { Category, ProductListItem } from "@/lib/api/types";

export async function CategorySection({
  category,
  products,
}: {
  category: Category;
  products: ProductListItem[];
}) {
  if (products.length === 0) return null;

  const t = await getTranslations("catalog");

  const tier = category.delivery_schedule_tier;
  const showTierLabel = tier === "same_day" || tier === "all_day";

  return (
    <section id={`category-${category.slug}`} className="scroll-mt-32 py-10">
      <div className="flex flex-wrap items-center gap-3">
        <h2 className="text-[32px] font-bold leading-[1.05] text-[#666] md:text-[32px]">
          {category.name}
        </h2>
        {showTierLabel ? (
          <span className="inline-flex shrink-0 items-center rounded-full bg-product-price-btn px-4 py-1.5 text-[16px] font-bold text-white">
            {t(`deliveryTier.${tier}`)}
          </span>
        ) : null}
      </div>
      {tier === "same_day" ? (
        <p className="mt-2 text-sm text-[var(--muted-2)]">{t("deliveryTierSameDayCutoff")}</p>
      ) : null}
      <div className="mt-8 grid gap-6 sm:grid-cols-2 xl:grid-cols-3">
        {products.map((p) => (
          <ProductCard key={p.id} product={p} />
        ))}
      </div>
    </section>
  );
}
