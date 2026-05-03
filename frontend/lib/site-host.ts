export function hostFromHeader(hostHeader: string | null): string {
  if (!hostHeader) return "";
  return hostHeader.split(":")[0].toLowerCase();
}

export function forwardedHostPeek(headerValue: string | null): string {
  if (!headerValue) return "";
  const first = headerValue.split(",")[0].trim();
  return hostFromHeader(first);
}

export function publicHostFromRequest(get: (name: string) => string | null): string {
  const fromForwarded = forwardedHostPeek(get("x-forwarded-host"));
  if (fromForwarded.length > 0) return fromForwarded;
  return hostFromHeader(get("host"));
}

export function isDevSweetChillHost(host: string): boolean {
  return host === "dev.sweet-chill.ge";
}

export function isMainSweetChillHost(host: string): boolean {
  return host === "sweet-chill.ge" || host === "www.sweet-chill.ge";
}
