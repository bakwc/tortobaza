"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useLocale } from "next-intl";
import { useState, type ReactNode } from "react";
import { setClientRequestLocale } from "@/lib/request-locale-shared";

function LocaleApiSync() {
  const locale = useLocale();
  setClientRequestLocale(locale);
  return null;
}

export function Providers({ children }: { children: ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30_000,
            refetchOnWindowFocus: false,
            retry: 1,
          },
        },
      }),
  );

  return (
    <QueryClientProvider client={queryClient}>
      <LocaleApiSync />
      {children}
    </QueryClientProvider>
  );
}
