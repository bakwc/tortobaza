"use client";

import { useLocale, useTranslations } from "next-intl";
import { useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardTitle, QueryState } from "@/components/menu/ui";
import { LeadsShell } from "@/components/leads/LeadsShell";
import { useTelegramMessages } from "@/hooks/useLeads";
import { Link, usePathname, useRouter } from "@/i18n/navigation";
import { formatCrmDateTime } from "@/lib/format";
import type { TelegramMessageKind } from "@/lib/api/types";

function parseKind(value: string | null): TelegramMessageKind {
  if (value === "keyword" || value === "all") return value;
  return "lead";
}

function senderLabel(senderUsername: string, senderId: number | null): string {
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
  kind: TelegramMessageKind,
  q: string,
  page: number,
): string {
  const params = new URLSearchParams();
  if (kind !== "lead") params.set("kind", kind);
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
  const kind = parseKind(searchParams.get("kind"));
  const q = searchParams.get("q") ?? "";
  const page = parsePage(searchParams.get("page"));
  const messages = useTelegramMessages(kind, q, page);
  const rows = messages.data?.results ?? [];

  const setParams = (nextKind: TelegramMessageKind, nextQ: string) => {
    const params = new URLSearchParams();
    if (nextKind !== "lead") params.set("kind", nextKind);
    const trimmed = nextQ.trim();
    if (trimmed) params.set("q", trimmed);
    const query = params.toString();
    router.replace(query ? `${pathname}?${query}` : pathname);
  };

  const kinds: { key: TelegramMessageKind; label: string }[] = [
    { key: "lead", label: t("kindLead") },
    { key: "keyword", label: t("kindKeyword") },
    { key: "all", label: t("kindAll") },
  ];

  return (
    <LeadsShell section="messages">
      <div className="grid gap-4">
        <Card>
          <div className="grid gap-4">
            <Input
              value={q}
              onChange={(event) => setParams(kind, event.target.value)}
              placeholder={t("filterPlaceholder")}
            />
            <div className="flex flex-wrap gap-2">
              {kinds.map((item) => (
                <Button
                  key={item.key}
                  type="button"
                  variant={item.key === kind ? "primary" : "outline"}
                  size="sm"
                  onClick={() => setParams(item.key, q)}
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
              <table className="mt-4 w-full text-sm">
                <thead className="text-left text-xs uppercase tracking-wide text-[var(--ink)]/50">
                  <tr>
                    <th className="py-2 pr-2">{t("sentAt")}</th>
                    <th className="py-2 pr-2">{t("channel")}</th>
                    <th className="py-2 pr-2">{t("sender")}</th>
                    <th className="py-2 pr-2">{t("text")}</th>
                    <th className="py-2" />
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row) => (
                    <tr key={row.id} className="border-t border-[var(--line)] align-top">
                      <td className="py-2 pr-2 whitespace-nowrap text-[var(--muted-2)]">
                        {formatCrmDateTime(row.sent_at, locale)}
                      </td>
                      <td className="py-2 pr-2">
                        {row.channel_title || row.channel_username}
                      </td>
                      <td className="py-2 pr-2 whitespace-nowrap">
                        {senderLabel(row.sender_username, row.sender_id)}
                      </td>
                      <td className="py-2 pr-2 max-w-md whitespace-pre-wrap">{row.text || "—"}</td>
                      <td className="py-2 text-right">
                        <a
                          href={row.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-sm font-medium text-[var(--brand)] hover:underline"
                        >
                          {t("openInTelegram")}
                        </a>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            {messages.data && rows.length > 0 ? (
              <div className="mt-4 flex items-center justify-between gap-3 text-sm text-[var(--ink)]">
                <span>{t("page", { page: messages.data.page, pages: messages.data.pages })}</span>
                <div className="flex gap-2">
                  {messages.data.page > 1 ? (
                    <Button asChild variant="outline" size="sm">
                      <Link href={pageHref(pathname, kind, q, messages.data.page - 1)}>{t("previous")}</Link>
                    </Button>
                  ) : null}
                  {messages.data.page < messages.data.pages ? (
                    <Button asChild variant="outline" size="sm">
                      <Link href={pageHref(pathname, kind, q, messages.data.page + 1)}>{t("next")}</Link>
                    </Button>
                  ) : null}
                </div>
              </div>
            ) : null}
          </QueryState>
        </Card>
      </div>
    </LeadsShell>
  );
}
