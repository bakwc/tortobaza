import Link from "next/link";
import { formatAed } from "@/lib/format";
import type { ProductListItem } from "@/lib/api/types";

export function ProductCard({ product }: { product: ProductListItem }) {
  return (
    <Link
      href={`/order/${product.slug}`}
      scroll={false}
      className="group flex flex-col overflow-hidden rounded-3xl bg-white shadow-sm ring-1 ring-[var(--line)] transition hover:shadow-md"
    >
      <div className="aspect-square w-full overflow-hidden bg-[var(--cream)]">
        {product.primary_image ? (
          <img
            src={product.primary_image}
            alt={product.name}
            className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-[1.03]"
            loading="lazy"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center text-[var(--muted-2)]">
            No image
          </div>
        )}
      </div>
      <div className="flex flex-1 flex-col gap-4 p-5">
        <h3 className="font-display text-xl text-[var(--ink)]">{product.name}</h3>
        <div className="mt-auto">
          <span className="inline-flex h-11 w-full items-center justify-center rounded-full bg-[var(--price)] px-6 text-sm font-medium text-white tracking-wide">
            {formatAed(product.base_price)}
          </span>
        </div>
      </div>
    </Link>
  );
}
