import Link from "next/link";
import { formatAed } from "@/lib/format";
import type { ProductListItem } from "@/lib/api/types";

export function ProductCard({ product }: { product: ProductListItem }) {
  return (
    <Link
      href={`/order/${product.slug}`}
      scroll={false}
      className="group flex flex-col bg-white p-5"
    >
      <div className="aspect-square w-full overflow-hidden bg-[var(--cream)]">
        {product.primary_image ? (
          <img
            src={product.primary_image.src}
            srcSet={product.primary_image.srcset}
            sizes="(max-width: 767px) 50vw, 33vw"
            alt={product.name}
            className="h-full w-full object-cover"
            loading="lazy"
            decoding="async"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center text-[var(--muted-2)]">
            No image
          </div>
        )}
      </div>
      <div className="flex flex-1 flex-col pt-5">
        <h3 className="text-[22px] font-normal leading-snug text-[#666]">
          {product.name}
        </h3>
        <div className="mt-6">
          <span className="inline-flex h-[36px] w-full items-center justify-center rounded-full bg-[#666] px-6 text-[14px] font-normal text-white">
            {formatAed(product.base_price)}
          </span>
        </div>
      </div>
    </Link>
  );
}
