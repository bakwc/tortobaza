"use client";

import { useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardTitle, NativeSelect, QueryState } from "@/components/menu/ui";
import { LeadMessageDialog } from "@/components/leads/LeadMessageDialog";
import { LeadsShell } from "@/components/leads/LeadsShell";
import { useSocialChannels, useSocialMessages } from "@/hooks/useLeads";
import { Link, usePathname, useRouter } from "@/i18n/navigation";
import { formatCrmDateTime } from "@/lib/format";
import type { SocialMessage, SocialMessageKind } from "@/lib/api/types";

function parseKind(value: string | null): SocialMessageKind {
  if (value === "keyword" || value === "all" || value === "potential") return value;
  return "lead";
}

function parseNetwork(value: string | null): string {
  return value ?? "";
}

function parseChannel(value: string | null): number | null {
  if (value === null || value === "") return null;
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return null;
  return Math.floor(parsed);
}

function senderLabel(senderUsername: string, senderId: string | null): string {
  if (senderUsername) return `@${senderUsername}`;
  if (senderId !== null) return String(senderId);
  return "—";
}

function parsePage(value: string | null): number {
  const parsed = Number(value ?? "1");
  if (!Number.isFinite(parsed) || parsed < 1) return 1;
  return Math.floor(parsed);
}

function pageHref(
  pathname: string,
  kind: SocialMessageKind,
  network: string,
  channel: number | null,
  q: string,
  page: number,
): string {
  const params = new URLSearchParams();
  if (kind !== "lead") params.set("kind", kind);
  if (network) params.set("network", network);
  if (channel !== null) params.set("channel", String(channel));
  const trimmed = q.trim();
  if (trimmed) params.set("q", trimmed);
  if (page > 1) params.set("page", String(page));
  const query = params.toString();
  return query ? `${pathname}?${query}` : pathname;
}

export function LeadsMessagesPanel() {
  const t = useTranslations("leads");
  const locale = useLocale();
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const [selected, setSelected] = useState<SocialMessage | null>(null);
  const kind = parseKind(searchParams.get("kind"));
  const network = parseNetwork(searchParams.get("network"));
  const channel = parseChannel(searchParams.get("channel"));
  const q = searchParams.get("q") ?? "";
  const page = parsePage(searchParams.get("page"));
  const channels = useSocialChannels();
  const messages = useSocialMessages(kind, network, channel, q, page);
  const rows = messages.data?.results ?? [];
  const channelRows = (channels.list.data ?? []).filter(
    (row) => network === "" || row.network_slug === network,
  );
  const networks: { slug: string; name: string }[] = [];
  const seenNetworks = new Set<string>();
  for (const row of channels.list.data ?? []) {
    if (seenNetworks.has(row.network_slug)) continue;
    seenNetworks.add(row.network_slug);
    networks.push({ slug: row.network_slug, name: row.network_name });
  }

  const setParams = (
    nextKind: SocialMessageKind,
    nextNetwork: string,
    nextChannel: number | null,
    nextQ: string,
  ) => {
    const params = new URLSearchParams();
    if (nextKind !== "lead") params.set("kind", nextKind);
    if (nextNetwork) params.set("network", nextNetwork);
    if (nextChannel !== null) params.set("channel", String(nextChannel));
    const trimmed = nextQ.trim();
    if (trimmed) params.set("q", trimmed);
    const query = params.toString();
    router.replace(query ? `${pathname}?${query}` : pathname);
  };

  const kinds: { key: SocialMessageKind; label: string }[] = [
    { key: "lead", label: t("kindLead") },
    { key: "potential", label: t("potential") },
    { key: "keyword", label: t("kindKeyword") },
    { key: "all", label: t("kindAll") },
  ];

  return (
    <LeadsShell section="messages">
      <div className="grid gap-4">
        <Card>
          <div className="grid gap-4">
            <div className="grid gap-3 sm:grid-cols-[1fr_200px_240px]">
              <Input
                value={q}
                onChange={(event) => setParams(kind, network, channel, event.target.value)}
                placeholder={t("filterPlaceholder")}
              />
              <NativeSelect
                value={network}
                onChange={(event) => setParams(kind, event.target.value, null, q)}
              >
                <option value="">{t("allNetworks")}</option>
                {networks.map((row) => (
                  <option key={row.slug} value={row.slug}>
                    {row.name}
                  </option>
                ))}
              </NativeSelect>
              <NativeSelect
                value={channel ?? ""}
                onChange={(event) => {
                  const raw = event.target.value;
                  setParams(kind, network, raw === "" ? null : Number(raw), q);
                }}
              >
                <option value="">{t("allChannels")}</option>
                {channelRows.map((row) => (
                  <option key={row.id} value={row.id}>
                    {`${row.network_name}: ${row.title || row.username}`}
                  </option>
                ))}
              </NativeSelect>
            </div>
            <div className="flex flex-wrap gap-2">
              {kinds.map((item) => (
                <Button
                  key={item.key}
                  type="button"
                  variant={item.key === kind ? "primary" : "outline"}
                  size="sm"
                  onClick={() => setParams(item.key, network, channel, q)}
                >
                  {item.label}
                </Button>
              ))}
            </div>
          </div>
        </Card>
        <Card>
          <CardTitle>{t("messages")}</CardTitle>
          <QueryState isLoading={messages.isLoading} isError={messages.isError}>
            {rows.length === 0 ? (
              <p className="mt-4 text-sm text-[var(--muted-2)]">{t("emptyMessages")}</p>
            ) : (
              <ul className="mt-4 divide-y divide-[var(--line)]">
                {rows.map((row) => (
                  <li key={row.id} className="py-4 first:pt-0 last:pb-0">
                    <button
                      type="button"
                      className="w-full text-left"
                      onClick={() => setSelected(row)}
                    >
                      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
                        <p className="min-w-0 text-sm">
                          <span className="font-medium text-[var(--ink)]">
                            {row.channel_title || row.channel_username}
                          </span>
                          <span className="text-[var(--muted-2)]"> · {row.network_name} · </span>
                          <span className="text-[var(--muted-2)]">
                            {senderLabel(row.sender_username, row.sender_id)}
                          </span>
                        </p>
                        <time className="shrink-0 text-xs text-[var(--muted-2)]">
                          {formatCrmDateTime(row.sent_at, locale)}
                        </time>
                      </div>
                      <p className="mt-2 max-w-3xl text-[15px] leading-relaxed whitespace-pre-wrap break-words text-[var(--ink)]">
                        {row.text || "—"}
                      </p>
                    </button>
                  </li>
                ))}
              </ul>
            )}
            {messages.data && rows.length > 0 ? (
              <div className="mt-4 flex items-center justify-between gap-3 border-t border-[var(--line)] pt-4 text-sm text-[var(--ink)]">
                <span>{t("page", { page: messages.data.page, pages: messages.data.pages })}</span>
                <div className="flex gap-2">
                  {messages.data.page > 1 ? (
                    <Button asChild variant="outline" size="sm">
                      <Link href={pageHref(pathname, kind, network, channel, q, messages.data.page - 1)}>
                        {t("previous")}
                      </Link>
                    </Button>
                  ) : null}
                  {messages.data.page < messages.data.pages ? (
                    <Button asChild variant="outline" size="sm">
                      <Link href={pageHref(pathname, kind, network, channel, q, messages.data.page + 1)}>
                        {t("next")}
                      </Link>
                    </Button>
                  ) : null}
                </div>
              </div>
            ) : null}
          </QueryState>
        </Card>
      </div>
      <LeadMessageDialog message={selected} onOpenChange={(open) => { if (!open) setSelected(null); }} />
    </LeadsShell>
  );
}
