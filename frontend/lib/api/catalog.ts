import "server-only";
import { publicApi } from "./public-api";
import type { ProductListItem } from "./types";

const PAGE_SIZE = 500;

export async function getAllProducts(params: {
  category?: string;
  search?: string;
} = {}): Promise<ProductListItem[]> {
  const results: ProductListItem[] = [];
  let page = 1;

  while (true) {
    const response = await publicApi.getProducts({
      ...params,
      page,
      page_size: PAGE_SIZE,
    });
    results.push(...response.results);
    if (!response.next) {
      break;
    }
    page += 1;
  }

  return results;
}
