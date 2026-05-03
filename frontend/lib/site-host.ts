export function hostFromHeader(hostHeader: string | null): string {
  if (!hostHeader) return "";
  return hostHeader.split(":")[0].toLowerCase();
}

export function isDevSweetChillHost(host: string): boolean {
  return host === "dev.sweet-chill.ge";
}

export function isMainSweetChillHost(host: string): boolean {
  return host === "sweet-chill.ge" || host === "www.sweet-chill.ge";
}
