let clientRequestLocale = "en";

export function getClientRequestLocale(): string {
  return clientRequestLocale;
}

export function setClientRequestLocale(locale: string): void {
  clientRequestLocale = locale;
}
