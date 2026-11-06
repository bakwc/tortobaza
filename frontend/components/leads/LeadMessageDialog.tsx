"use client";

import { useLocale, useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { formatCrmDateTime } from "@/lib/format";
import type { SocialMessage, SocialMessageProcessingEvent } from "@/lib/api/types";

function senderLabel(senderUsername: string, senderId: string | null): string {
  if (senderUsername) return `@${senderUsername}`;
  if (senderId !== null) return String(senderId);
  return "—";
}

function flagText(value: boolean | null, yes: string, no: string, pending: string): string {
  if (value === null) return pending;
  if (value) return yes;
  return no;
}

function historyTitle(
  event: SocialMessageProcessingEvent,
  found: string,
  context: string,
  lead: string,
  verify: string,
): string {
  if (event.kind === "found") return found;
  if (event.kind === "context") return context;
  if (event.classifier === "lead") return lead;
  return verify;
}

export function LeadMessageDialog({
  message,
  onOpenChange,
}: {
  message: SocialMessage | null;
  onOpenChange: (open: boolean) => void;
}) {
  const t = useTranslations("leads");
  const locale = useLocale();
  const context = message?.context ?? [];

  return (
    <Dialog open={message !== null} onOpenChange={onOpenChange}>
      <DialogContent className="w-[min(720px,calc(100vw-1.5rem))]">
        <div className="max-h-[calc(100vh-3rem)] overflow-y-auto p-6">
          <DialogTitle className="pr-10 text-lg font-semibold text-[var(--ink)]">
            {message ? message.channel_title || message.channel_username : t("messages")}
          </DialogTitle>
          {message ? (
            <>
            <p className="mt-1 text-sm text-[var(--muted-2)]">
              {message.network_name}
              {" · "}
              {senderLabel(message.sender_username, message.sender_id)}
              {" · "}
              {formatCrmDateTime(message.sent_at, locale)}
            </p>
            <dl className="mt-4 grid gap-3 text-sm">
              <div>
                <dt className="text-[var(--muted-2)]">{t("location")}</dt>
                <dd className="text-[var(--ink)]">{message.location || "—"}</dd>
              </div>
              <div>
                <dt className="text-[var(--muted-2)]">{t("topic")}</dt>
                <dd className="text-[var(--ink)]">{message.topic || "—"}</dd>
              </div>
            </dl>
            <p className="mt-4 whitespace-pre-wrap break-words text-[15px] leading-relaxed text-[var(--ink)]">
              {message.text || "—"}
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              <span className="rounded-full bg-[var(--cream)] px-2.5 py-0.5 text-xs font-semibold text-[var(--ink)]/70">
                {`${t("keywordMatch")}: ${flagText(message.keyword_match, t("yes"), t("no"), t("pending"))}`}
              </span>
              <span className="rounded-full bg-[var(--cream)] px-2.5 py-0.5 text-xs font-semibold text-[var(--ink)]/70">
                {`${t("potentialLead")}: ${flagText(message.potential_lead, t("yes"), t("no"), t("pending"))}`}
              </span>
              <span className="rounded-full bg-[var(--cream)] px-2.5 py-0.5 text-xs font-semibold text-[var(--ink)]/70">
                {`${t("lead")}: ${flagText(message.lead, t("yes"), t("no"), t("pending"))}`}
              </span>
            </div>
            <h3 className="mt-6 text-sm font-semibold text-[var(--ink)]">{t("history")}</h3>
            {message.processing_history.length === 0 ? (
              <p className="mt-2 text-sm text-[var(--muted-2)]">{t("emptyHistory")}</p>
            ) : (
              <ul className="mt-2 divide-y divide-[var(--line)]">
                {message.processing_history.map((event, index) => (
                  <li key={`${event.at}-${index}`} className="py-3">
                    <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
                      <p className="text-sm font-medium text-[var(--ink)]">
                        {historyTitle(
                          event,
                          t("historyFound"),
                          t("historyContext"),
                          t("historyClassifierLead"),
                          t("historyClassifierVerify"),
                        )}
                      </p>
                      <time className="shrink-0 text-xs text-[var(--muted-2)]">
                        {formatCrmDateTime(event.at, locale)}
                      </time>
                    </div>
                    {event.kind === "classify" ? (
                      <p className="mt-2 whitespace-pre-wrap break-words text-sm leading-relaxed text-[var(--ink)]">
                        {`${flagText(event.verdict, t("yes"), t("no"), t("pending"))}. ${event.explanation}`}
                      </p>
                    ) : null}
                  </li>
                ))}
              </ul>
            )}
            <h3 className="mt-6 text-sm font-semibold text-[var(--ink)]">{t("context")}</h3>
            {context.length === 0 ? (
              <p className="mt-2 text-sm text-[var(--muted-2)]">{t("emptyContext")}</p>
            ) : (
              <ul className="mt-2 divide-y divide-[var(--line)]">
                {context.map((post) => {
                  const target = post.url === message.url;
                  return (
                    <li
                      key={post.url}
                      className={target ? "bg-[var(--cream)] px-3 py-3" : "py-3"}
                    >
                      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
                        <p className="text-sm font-medium text-[var(--ink)]">
                          {post.username ? `@${post.username}` : "—"}
                          {target ? (
                            <span className="ml-2 text-xs font-semibold text-[var(--brand)]">
                              {t("target")}
                            </span>
                          ) : null}
                        </p>
                        <time className="shrink-0 text-xs text-[var(--muted-2)]">
                          {formatCrmDateTime(post.sent_at, locale)}
                        </time>
                      </div>
                      <p className="mt-2 whitespace-pre-wrap break-words text-sm leading-relaxed text-[var(--ink)]">
                        {post.text || "—"}
                      </p>
                    </li>
                  );
                })}
              </ul>
            )}
            <div className="mt-6 flex justify-end">
              <Button asChild variant="outline" size="sm">
                <a href={message.url} target="_blank" rel="noopener noreferrer">
                  {t("open")}
                </a>
              </Button>
            </div>
            </>
          ) : null}
        </div>
      </DialogContent>
    </Dialog>
  );
}
