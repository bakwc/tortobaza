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
    <section id={`category-${category.slug}`} className="scroll-mt-32 py-8">
      <h2 className="font-display text-3xl font-semibold text-[var(--ink)] md:text-4xl">
        {category.name}
      </h2>
      <div className="mt-6 grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
        {products.map((p) => (
          <ProductCard key={p.id} product={p} />
        ))}
      </div>
    </section>
  );
}
