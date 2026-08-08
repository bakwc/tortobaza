"use client";

import { createContext, useContext, type ReactNode } from "react";
import type { Locale } from "@/i18n/routing";

export type LocaleAlternates = Partial<Record<Locale, string>>;

const LocaleAlternatesContext = createContext<LocaleAlternates | null>(null);

export function LocaleAlternatesProvider({
  alternates,
  children,
}: {
  alternates: LocaleAlternates;
  children: ReactNode;
}) {
  return (
    <LocaleAlternatesContext.Provider value={alternates}>
      {children}
    </LocaleAlternatesContext.Provider>
  );
}

export function useLocaleAlternates(): LocaleAlternates | null {
  return useContext(LocaleAlternatesContext);
}
