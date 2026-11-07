"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { EditorDialog } from "@/components/menu/EditorDialog";
import { Card, CardTitle, CheckboxField, Field, NativeSelect, QueryState } from "@/components/menu/ui";
import { LeadsShell } from "@/components/leads/LeadsShell";
import { useCan } from "@/hooks/useAuth";
import { useSocialSearchQueries, useSocialVerticals } from "@/hooks/useLeads";
import type {
  LeadVertical,
  LeadVerticalBody,
  SocialSearchQuery,
  SocialSearchQueryBody,
} from "@/lib/api/types";

const emptyVertical: LeadVerticalBody = {
  slug: "",
  name: "",
  enabled: true,
  telegram_chat_id: "",
  prompt_classify: "",
  prompt_geo: "",
  prompt_context: "",
  prompt_profile: "",
};

const emptyQuery: SocialSearchQueryBody = {
  query: "",
  kind: "heavy",
  recent: false,
  post_limit: 50,
  enabled: true,
  position: 0,
};

function verticalBody(row: LeadVertical): LeadVerticalBody {
  return {
    slug: row.slug,
    name: row.name,
    enabled: row.enabled,
    telegram_chat_id: row.telegram_chat_id,
    prompt_classify: row.prompt_classify,
    prompt_geo: row.prompt_geo,
    prompt_context: row.prompt_context,
    prompt_profile: row.prompt_profile,
  };
}

function queryBody(row: SocialSearchQuery): SocialSearchQueryBody {
  return {
    query: row.query,
    kind: row.kind,
    recent: row.recent,
    post_limit: row.post_limit,
    enabled: row.enabled,
    position: row.position,
  };
}

export function LeadsVerticalsPanel() {
  const t = useTranslations("leads");
  const stock = useTranslations("stock");
  const canEdit = useCan("edit_leads");
  const verticals = useSocialVerticals();
  const queries = useSocialSearchQueries();
  const [verticalId, setVerticalId] = useState<number | null>(null);
  const [verticalDraft, setVerticalDraft] = useState<LeadVerticalBody | null>(null);
  const [queryId, setQueryId] = useState<number | null>(null);
  const [queryDraft, setQueryDraft] = useState<SocialSearchQueryBody | null>(null);

  const openVertical = (row: LeadVertical | null) => {
    verticals.save.reset();
    verticals.remove.reset();
    setVerticalId(row ? row.id : null);
    setVerticalDraft(row ? verticalBody(row) : emptyVertical);
  };

  const openQuery = (row: SocialSearchQuery | null) => {
    queries.save.reset();
    queries.remove.reset();
    setQueryId(row ? row.id : null);
    setQueryDraft(row ? queryBody(row) : emptyQuery);
  };

  const verticalRows = verticals.list.data ?? [];
  const queryRows = queries.list.data ?? [];

  return (
    <LeadsShell section="verticals">
      <div className="grid gap-6">
        <Card>
          <div className="flex items-center justify-between gap-3">
            <CardTitle>{t("verticals")}</CardTitle>
            {canEdit ? (
              <Button type="button" size="sm" onClick={() => openVertical(null)}>
                <Plus className="mr-1 h-4 w-4" />
                {t("addVertical")}
              </Button>
            ) : null}
          </div>
          <QueryState isLoading={verticals.list.isLoading} isError={verticals.list.isError}>
            {verticalRows.length === 0 ? (
              <p className="mt-4 text-sm text-[var(--muted-2)]">{t("emptyVerticals")}</p>
            ) : (
              <table className="mt-4 w-full text-sm">
                <thead className="text-left text-xs uppercase tracking-wide text-[var(--ink)]/50">
                  <tr>
                    <th className="py-2">{t("title")}</th>
                    <th className="py-2">{t("chatId")}</th>
                    <th className="py-2">{t("enabled")}</th>
                  </tr>
                </thead>
                <tbody>
                  {verticalRows.map((row) => (
                    <tr
                      key={row.id}
                      onClick={() => openVertical(row)}
                      className="cursor-pointer border-t border-[var(--line)] hover:bg-[var(--cream)]"
                    >
                      <td className="py-2">{row.name}</td>
                      <td className="py-2">{row.telegram_chat_id || "—"}</td>
                      <td className="py-2">{row.enabled ? stock("yes") : stock("no")}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </QueryState>
        </Card>
        <Card>
          <div className="flex items-center justify-between gap-3">
            <CardTitle>{t("searchQueries")}</CardTitle>
            {canEdit ? (
              <Button type="button" size="sm" onClick={() => openQuery(null)}>
                <Plus className="mr-1 h-4 w-4" />
                {t("addQuery")}
              </Button>
            ) : null}
          </div>
          <QueryState isLoading={queries.list.isLoading} isError={queries.list.isError}>
            {queryRows.length === 0 ? (
              <p className="mt-4 text-sm text-[var(--muted-2)]">{t("emptyQueries")}</p>
            ) : (
              <table className="mt-4 w-full text-sm">
                <thead className="text-left text-xs uppercase tracking-wide text-[var(--ink)]/50">
                  <tr>
                    <th className="py-2">{t("query")}</th>
                    <th className="py-2">{t("kind")}</th>
                    <th className="py-2">{t("postLimit")}</th>
                    <th className="py-2">{t("enabled")}</th>
                  </tr>
                </thead>
                <tbody>
                  {queryRows.map((row) => (
                    <tr
                      key={row.id}
                      onClick={() => openQuery(row)}
                      className="cursor-pointer border-t border-[var(--line)] hover:bg-[var(--cream)]"
                    >
                      <td className="py-2">{row.query}</td>
                      <td className="py-2">{row.kind === "heavy" ? t("kindHeavy") : t("kindLight")}</td>
                      <td className="py-2">{row.post_limit}</td>
                      <td className="py-2">{row.enabled ? stock("yes") : stock("no")}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </QueryState>
        </Card>
        {verticalDraft !== null ? (
          <EditorDialog
            open
            onOpenChange={(value) => (value ? null : setVerticalDraft(null))}
            onCancel={null}
            title={verticalId === null ? t("newVertical") : verticalDraft.name}
            pending={verticals.save.isPending}
            error={verticals.save.error ?? verticals.remove.error}
            submitLabel={canEdit ? stock("save") : null}
            onSubmit={() =>
              verticals.save.mutate(
                {
                  id: verticalId,
                  body: {
                    ...verticalDraft,
                    slug: verticalDraft.slug.trim(),
                    name: verticalDraft.name.trim(),
                    telegram_chat_id: verticalDraft.telegram_chat_id.trim(),
                  },
                },
                { onSuccess: () => setVerticalDraft(null) },
              )
            }
            onDelete={
              canEdit && verticalId !== null
                ? () => verticals.remove.mutate(verticalId, { onSuccess: () => setVerticalDraft(null) })
                : null
            }
            deletePending={verticals.remove.isPending}
            headerAction={null}
            below={null}
          >
            <div className="grid gap-4">
              <Field label={t("slug")}>
                <Input
                  required
                  value={verticalDraft.slug}
                  onChange={(event) => setVerticalDraft({ ...verticalDraft, slug: event.target.value })}
                />
              </Field>
              <Field label={t("title")}>
                <Input
                  required
                  value={verticalDraft.name}
                  onChange={(event) => setVerticalDraft({ ...verticalDraft, name: event.target.value })}
                />
              </Field>
              <Field label={t("chatId")}>
                <Input
                  value={verticalDraft.telegram_chat_id}
                  onChange={(event) =>
                    setVerticalDraft({ ...verticalDraft, telegram_chat_id: event.target.value })
                  }
                />
              </Field>
              <CheckboxField
                label={t("enabled")}
                checked={verticalDraft.enabled}
                onChange={(value) => setVerticalDraft({ ...verticalDraft, enabled: value })}
              />
              <Field label={t("promptClassify")}>
                <Textarea
                  required
                  value={verticalDraft.prompt_classify}
                  onChange={(event) =>
                    setVerticalDraft({ ...verticalDraft, prompt_classify: event.target.value })
                  }
                />
              </Field>
              <Field label={t("promptGeo")}>
                <Textarea
                  required
                  value={verticalDraft.prompt_geo}
                  onChange={(event) => setVerticalDraft({ ...verticalDraft, prompt_geo: event.target.value })}
                />
              </Field>
              <Field label={t("promptContext")}>
                <Textarea
                  required
                  value={verticalDraft.prompt_context}
                  onChange={(event) =>
                    setVerticalDraft({ ...verticalDraft, prompt_context: event.target.value })
                  }
                />
              </Field>
              <Field label={t("promptProfile")}>
                <Textarea
                  required
                  value={verticalDraft.prompt_profile}
                  onChange={(event) =>
                    setVerticalDraft({ ...verticalDraft, prompt_profile: event.target.value })
                  }
                />
              </Field>
            </div>
          </EditorDialog>
        ) : null}
        {queryDraft !== null ? (
          <EditorDialog
            open
            onOpenChange={(value) => (value ? null : setQueryDraft(null))}
            onCancel={null}
            title={queryId === null ? t("newQuery") : queryDraft.query}
            pending={queries.save.isPending}
            error={queries.save.error ?? queries.remove.error}
            submitLabel={canEdit ? stock("save") : null}
            onSubmit={() =>
              queries.save.mutate(
                {
                  id: queryId,
                  body: {
                    ...queryDraft,
                    query: queryDraft.query.trim(),
                    post_limit: Number(queryDraft.post_limit),
                    position: Number(queryDraft.position),
                  },
                },
                { onSuccess: () => setQueryDraft(null) },
              )
            }
            onDelete={
              canEdit && queryId !== null
                ? () => queries.remove.mutate(queryId, { onSuccess: () => setQueryDraft(null) })
                : null
            }
            deletePending={queries.remove.isPending}
            headerAction={null}
            below={null}
          >
            <div className="grid gap-4">
              <Field label={t("query")}>
                <Input
                  required
                  value={queryDraft.query}
                  onChange={(event) => setQueryDraft({ ...queryDraft, query: event.target.value })}
                />
              </Field>
              <Field label={t("kind")}>
                <NativeSelect
                  value={queryDraft.kind}
                  onChange={(event) =>
                    setQueryDraft({
                      ...queryDraft,
                      kind: event.target.value === "light" ? "light" : "heavy",
                    })
                  }
                >
                  <option value="heavy">{t("kindHeavy")}</option>
                  <option value="light">{t("kindLight")}</option>
                </NativeSelect>
              </Field>
              <Field label={t("postLimit")}>
                <Input
                  required
                  type="number"
                  min={1}
                  value={queryDraft.post_limit}
                  onChange={(event) =>
                    setQueryDraft({ ...queryDraft, post_limit: Number(event.target.value) })
                  }
                />
              </Field>
              <Field label={t("position")}>
                <Input
                  required
                  type="number"
                  min={0}
                  value={queryDraft.position}
                  onChange={(event) =>
                    setQueryDraft({ ...queryDraft, position: Number(event.target.value) })
                  }
                />
              </Field>
              <CheckboxField
                label={t("recent")}
                checked={queryDraft.recent}
                onChange={(value) => setQueryDraft({ ...queryDraft, recent: value })}
              />
              <CheckboxField
                label={t("enabled")}
                checked={queryDraft.enabled}
                onChange={(value) => setQueryDraft({ ...queryDraft, enabled: value })}
              />
            </div>
          </EditorDialog>
        ) : null}
      </div>
    </LeadsShell>
  );
}
