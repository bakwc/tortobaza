"use client";

import { useLocale, useTranslations } from "next-intl";
import { useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardTitle, QueryState } from "@/components/menu/ui";
import { LeadsShell } from "@/components/leads/LeadsShell";
import { useTelegramMessages } from "@/hooks/useLeads";
import { usePathname, useRouter } from "@/i18n/navigation";
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

export function LeadsMessagesPanel() {
  const t = useTranslations("leads");
  const locale = useLocale();
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const kind = parseKind(searchParams.get("kind"));
  const q = searchParams.get("q") ?? "";
  const messages = useTelegramMessages(kind, q);

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
            {(messages.data ?? []).length === 0 ? (
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
                  {(messages.data ?? []).map((row) => (
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
          </QueryState>
        </Card>
      </div>
    </LeadsShell>
  );
}
