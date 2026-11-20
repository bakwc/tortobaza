function fold(value: string): string {
  return value.toLowerCase().replaceAll("ё", "е");
}

export function nameMatches(label: string, query: string): boolean {
  const needle = fold(query).trim();
  if (needle === "") return true;
  const haystack = fold(label);
  return needle.split(/\s+/).every((token) => haystack.includes(token));
}

export function namesEqual(left: string, right: string): boolean {
  return fold(left).trim() === fold(right).trim();
}
