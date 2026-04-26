import { clientFetch } from "./client";
import { endpoints, type Fetcher } from "./endpoints";

const clientFetcher: Fetcher = (path, options) =>
  clientFetch(path, {
    method: options?.method,
    body: options?.body,
    searchParams: options?.searchParams,
    headers: options?.headers,
    cache: options?.cache,
    next: options?.next,
  });

export const api = endpoints(clientFetcher);

export type { Fetcher };
