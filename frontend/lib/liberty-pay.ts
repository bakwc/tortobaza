import type { StartPaymentResponse } from "@/lib/api/types";

export function submitLibertyPaymentForm(response: StartPaymentResponse): void {
  const form = document.createElement("form");
  form.method = "POST";
  form.action = response.action_url;
  for (const [name, value] of Object.entries(response.fields)) {
    const input = document.createElement("input");
    input.type = "hidden";
    input.name = name;
    input.value = value;
    form.appendChild(input);
  }
  document.body.appendChild(form);
  form.submit();
}

export function parseLibertyCustomdata(customdata: string | null): { number: string; token: string } | null {
  if (!customdata) return null;
  const separator = customdata.indexOf("|");
  if (separator <= 0) return null;
  const number = customdata.slice(0, separator);
  const token = customdata.slice(separator + 1);
  if (!number || !token) return null;
  return { number, token };
}
