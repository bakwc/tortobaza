"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { EditorDialog } from "@/components/menu/EditorDialog";
import { Card, CardTitle, CheckboxField, Field, QueryState } from "@/components/menu/ui";
import { LeadsShell } from "@/components/leads/LeadsShell";
import { useCan } from "@/hooks/useAuth";
import { useSocialChannels } from "@/hooks/useLeads";
import type { SocialChannel, SocialChannelBody } from "@/lib/api/types";

export function LeadsChannelsPanel() {
  const t = useTranslations("leads");
  const stock = useTranslations("stock");
  const canEdit = useCan("edit_leads");
  const channels = useSocialChannels();
  const rows = (channels.list.data ?? []).filter((row) => row.network_slug === "telegram");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [draft, setDraft] = useState<SocialChannelBody | null>(null);

  const open = (row: SocialChannel | null) => {
    channels.save.reset();
    channels.remove.reset();
    setEditingId(row ? row.id : null);
    setDraft(row ? { username: row.username, enabled: row.enabled } : { username: "", enabled: true });
  };

  const close = () => setDraft(null);

  return (
    <LeadsShell section="channels">
      <div className="grid gap-6">
        <Card>
          <div className="flex items-center justify-between gap-3">
            <CardTitle>{t("channels")}</CardTitle>
            {canEdit ? (
              <Button type="button" size="sm" onClick={() => open(null)}>
                <Plus className="mr-1 h-4 w-4" />
                {t("addChannel")}
              </Button>
            ) : null}
          </div>
          <QueryState isLoading={channels.list.isLoading} isError={channels.list.isError}>
            {rows.length === 0 ? (
              <p className="mt-4 text-sm text-[var(--muted-2)]">{t("emptyChannels")}</p>
            ) : (
              <table className="mt-4 w-full text-sm">
                <thead className="text-left text-xs uppercase tracking-wide text-[var(--ink)]/50">
                  <tr>
                    <th className="py-2">{t("username")}</th>
                    <th className="py-2">{t("title")}</th>
                    <th className="py-2">{t("enabled")}</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row) => (
                    <tr
                      key={row.id}
                      onClick={() => open(row)}
                      className="cursor-pointer border-t border-[var(--line)] hover:bg-[var(--cream)]"
                    >
                      <td className="py-2">{row.username}</td>
                      <td className="py-2">{row.title || "—"}</td>
                      <td className="py-2">{row.enabled ? stock("yes") : stock("no")}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </QueryState>
        </Card>
        {draft !== null ? (
          <EditorDialog
            open
            onOpenChange={(value) => (value ? null : close())}
            onCancel={null}
            title={editingId === null ? t("newChannel") : draft.username}
            pending={channels.save.isPending}
            error={channels.save.error ?? channels.remove.error}
            submitLabel={canEdit ? stock("save") : null}
            onSubmit={() =>
              channels.save.mutate(
                { id: editingId, body: { username: draft.username.trim(), enabled: draft.enabled } },
                { onSuccess: close },
              )
            }
            onDelete={
              canEdit && editingId !== null
                ? () => channels.remove.mutate(editingId, { onSuccess: close })
                : null
            }
            deletePending={channels.remove.isPending}
            headerAction={null}
            below={null}
          >
            <div className="grid gap-4">
              <Field label={t("username")}>
                <Input
                  required
                  value={draft.username}
                  onChange={(event) => setDraft({ ...draft, username: event.target.value })}
                />
              </Field>
              <CheckboxField
                label={t("enabled")}
                checked={draft.enabled}
                onChange={(value) => setDraft({ ...draft, enabled: value })}
              />
            </div>
          </EditorDialog>
        ) : null}
      </div>
    </LeadsShell>
  );
}
