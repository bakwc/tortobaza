import { ProductCard } from "./ProductCard";
import type { Category, ProductListItem } from "@/lib/api/types";

export function CategorySection({
  category,
  products,
}: {
  category: Category;
  products: ProductListItem[];
}) {
  if (products.length === 0) return null;

  return (
    <section id={`category-${category.slug}`} className="scroll-mt-32 py-10">
      <h2 className="text-[32px] font-bold leading-[1.05] text-[#666] md:text-[32px]">
        {category.name}
      </h2>
      <div className="mt-8 grid gap-6 sm:grid-cols-2 xl:grid-cols-3">
        {products.map((p) => (
          <ProductCard key={p.id} product={p} />
        ))}
      </div>
    </section>
  );
}
