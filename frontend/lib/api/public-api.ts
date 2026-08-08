import "server-only";
import { endpoints, type Fetcher } from "./endpoints";
import { publicServerFetch } from "./public-server";

const publicFetcher: Fetcher = (path, options) =>
  publicServerFetch(path, {
    method: options?.method,
    body: options?.body,
    searchParams: options?.searchParams,
    headers: options?.headers,
    cache: options?.cache,
    next: options?.next,
  });

export const publicApi = endpoints(publicFetcher);
