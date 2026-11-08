export const INVALID_FIELDS_CLASS =
  "[&[data-validated]_:is(input,textarea,select):invalid]:border-[var(--danger)] [&[data-validated]_:is(input,textarea,select):invalid]:bg-red-50 [&[data-validated]_input:invalid+input]:border-[var(--danger)] [&[data-validated]_input:invalid+input]:bg-red-50";

type FormControl = HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement;

export type FieldProblems = { missing: string[]; invalid: string[] };

type LocatedError = { path: (string | number)[]; message: string };

function labelText(element: Element): string {
  const text = element.closest("label")?.querySelector("span")?.textContent?.trim() ?? "";
  return text.replace(/ \*$/, "");
}

export function invalidFieldName(element: Element): string {
  const parts: string[] = [];
  let group = element.parentElement?.closest<HTMLElement>("[data-field-group]");
  while (group) {
    parts.unshift(group.dataset.fieldGroup as string);
    group = group.parentElement?.closest<HTMLElement>("[data-field-group]");
  }
  const target = element.getAttribute("aria-hidden") === "true" ? element.nextElementSibling : element;
  const label = labelText(element);
  parts.push(label !== "" ? label : (target?.getAttribute("placeholder") ?? ""));
  return parts.filter((part) => part !== "").join(" → ");
}

function scrollTarget(element: Element): Element {
  return element.getAttribute("aria-hidden") === "true" && element.nextElementSibling
    ? element.nextElementSibling
    : element;
}

function isControl(element: Element | null): element is FormControl {
  return (
    element instanceof HTMLInputElement ||
    element instanceof HTMLTextAreaElement ||
    element instanceof HTMLSelectElement
  );
}

export function clearCustomValidity(form: HTMLFormElement): void {
  for (const element of form.querySelectorAll("input, textarea, select")) {
    if (isControl(element)) element.setCustomValidity("");
  }
}

export function collectFieldProblems(form: HTMLFormElement): FieldProblems {
  const invalid = Array.from(form.querySelectorAll("input:invalid, textarea:invalid, select:invalid")).filter(isControl);
  if (invalid.length > 0) {
    scrollTarget(invalid[0]).scrollIntoView({ behavior: "smooth", block: "center" });
  }
  const missing: string[] = [];
  const bad: string[] = [];
  for (const element of invalid) {
    const name = invalidFieldName(element);
    if (element.validity.valueMissing) missing.push(name);
    else bad.push(name);
  }
  return { missing: [...new Set(missing)], invalid: [...new Set(bad)] };
}

export function formatFieldProblems(
  problems: FieldProblems,
  missingLabel: (fields: string) => string,
  invalidLabel: (fields: string) => string,
): string[] {
  const messages: string[] = [];
  if (problems.missing.length > 0) messages.push(missingLabel(problems.missing.join(", ")));
  if (problems.invalid.length > 0) messages.push(invalidLabel(problems.invalid.join(", ")));
  return messages;
}

function directMessages(value: unknown): string[] | null {
  if (typeof value === "string") return [value];
  if (Array.isArray(value) && value.every((item) => typeof item === "string")) return value;
  return null;
}

function walk(value: unknown, path: (string | number)[], out: LocatedError[]): void {
  const direct = directMessages(value);
  if (direct !== null) {
    for (const message of direct) out.push({ path, message });
    return;
  }
  if (Array.isArray(value)) {
    value.forEach((item, index) => walk(item, [...path, index], out));
    return;
  }
  if (value && typeof value === "object") {
    for (const [key, item] of Object.entries(value)) walk(item, [...path, key], out);
  }
}

function fieldFor(form: HTMLFormElement, path: (string | number)[]): FormControl | null {
  const segments = path.at(-1) === "non_field_errors" ? path.slice(0, -1) : path;
  let scope: ParentNode = form;
  let field: string | null = null;
  for (let i = 0; i < segments.length; i++) {
    const segment = segments[i];
    if (typeof segment === "number") {
      const listKey = segments[i - 1];
      if (typeof listKey !== "string") return null;
      const row = scope.querySelectorAll<HTMLElement>(`[data-error-list="${CSS.escape(listKey)}"]`)[segment];
      if (row === undefined) return null;
      scope = row;
      field = null;
      continue;
    }
    if (typeof segments[i + 1] === "number") continue;
    field = segment;
  }
  if (field === null) return null;
  const found = scope.querySelector(`[name="${CSS.escape(field)}"]`);
  return isControl(found) ? found : null;
}

function pathLabel(path: (string | number)[], rowLabel: (index: number) => string): string {
  const segments = path.at(-1) === "non_field_errors" ? path.slice(0, -1) : path;
  const parts: string[] = [];
  for (let i = 0; i < segments.length; i++) {
    const segment = segments[i];
    if (typeof segment === "number") parts.push(rowLabel(segment));
    else if (typeof segments[i + 1] !== "number") parts.push(segment);
  }
  return parts.join(" → ");
}

export function applyServerErrors(
  form: HTMLFormElement,
  parsed: unknown,
  rowLabel: (index: number) => string,
): string[] {
  clearCustomValidity(form);
  const found: LocatedError[] = [];
  walk(parsed, [], found);
  const lines: string[] = [];
  let scrolled = false;
  for (const item of found) {
    const element = fieldFor(form, item.path);
    if (element !== null) {
      element.setCustomValidity(item.message);
      if (!scrolled) {
        scrollTarget(element).scrollIntoView({ behavior: "smooth", block: "center" });
        scrolled = true;
      }
      const name = invalidFieldName(element);
      lines.push(name === "" ? item.message : `${name}: ${item.message}`);
    } else {
      const label = pathLabel(item.path, rowLabel);
      lines.push(label === "" ? item.message : `${label}: ${item.message}`);
    }
  }
  return lines;
}

export function listRowMessages(parsed: unknown, listKey: string): string[][] {
  const found: LocatedError[] = [];
  walk(parsed, [], found);
  const rows = new Map<number, string[]>();
  for (const item of found) {
    if (item.path[0] !== listKey || typeof item.path[1] !== "number") continue;
    const index = item.path[1];
    const current = rows.get(index) ?? [];
    current.push(item.message);
    rows.set(index, current);
  }
  const max = Math.max(-1, ...rows.keys());
  return Array.from({ length: max + 1 }, (_, index) => rows.get(index) ?? []);
}
