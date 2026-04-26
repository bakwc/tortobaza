import "server-only";
import { serverFetch } from "./server";
import { endpoints, type Fetcher } from "./endpoints";

const serverFetcher: Fetcher = (path, options) =>
  serverFetch(path, {
    method: options?.method,
    body: options?.body,
    searchParams: options?.searchParams,
    headers: options?.headers,
    cache: options?.cache,
    next: options?.next,
  });

export const serverApi = endpoints(serverFetcher);
