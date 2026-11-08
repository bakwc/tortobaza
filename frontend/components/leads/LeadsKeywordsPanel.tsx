"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { EditorDialog } from "@/components/menu/EditorDialog";
import { Card, CardTitle, Field, NativeSelect, QueryState } from "@/components/menu/ui";
import { LeadsShell } from "@/components/leads/LeadsShell";
import { useCan } from "@/hooks/useAuth";
import { useSocialKeywords, useSocialVerticals } from "@/hooks/useLeads";
import type { SocialKeyword, SocialKeywordBody } from "@/lib/api/types";

export function LeadsKeywordsPanel() {
  const t = useTranslations("leads");
  const stock = useTranslations("stock");
  const canEdit = useCan("edit_leads");
  const verticals = useSocialVerticals();
  const verticalRows = verticals.list.data ?? [];
  const [verticalId, setVerticalId] = useState<number | null>(null);
  const selected = verticalId ?? verticalRows[0]?.id ?? null;
  const keywords = useSocialKeywords(selected);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [draft, setDraft] = useState<SocialKeywordBody | null>(null);
  const [verticalHint, setVerticalHint] = useState(false);

  const open = (row: SocialKeyword | null) => {
    if (selected === null) {
      setVerticalHint(true);
      return;
    }
    setVerticalHint(false);
    keywords.save.reset();
    keywords.remove.reset();
    setEditingId(row ? row.id : null);
    setDraft(row ? { word: row.word, vertical: row.vertical } : { word: "", vertical: selected });
  };

  const close = () => setDraft(null);

  return (
    <LeadsShell section="keywords">
      <div className="grid gap-6">
        <Card>
          <div className="flex items-center justify-between gap-3">
            <CardTitle>{t("keywords")}</CardTitle>
            <NativeSelect
              className="w-auto max-w-xs"
              value={selected ?? ""}
              onChange={(event) => setVerticalId(Number(event.target.value))}
            >
              {verticalRows.map((row) => (
                <option key={row.id} value={row.id}>
                  {row.name}
                </option>
              ))}
            </NativeSelect>
            {canEdit ? (
              <Button type="button" size="sm" onClick={() => open(null)}>
                <Plus className="mr-1 h-4 w-4" />
                {t("addKeyword")}
              </Button>
            ) : null}
          </div>
          {verticalHint ? (
            <p className="mt-3 text-sm font-medium text-[var(--danger)]">{t("chooseVertical")}</p>
          ) : null}
          <QueryState isLoading={keywords.list.isLoading} isError={keywords.list.isError}>
            {(keywords.list.data ?? []).length === 0 ? (
              <p className="mt-4 text-sm text-[var(--muted-2)]">{t("emptyKeywords")}</p>
            ) : (
              <table className="mt-4 w-full text-sm">
                <thead className="text-left text-xs uppercase tracking-wide text-[var(--ink)]/50">
                  <tr>
                    <th className="py-2">{t("word")}</th>
                  </tr>
                </thead>
                <tbody>
                  {(keywords.list.data ?? []).map((row) => (
                    <tr
                      key={row.id}
                      onClick={() => open(row)}
                      className="cursor-pointer border-t border-[var(--line)] hover:bg-[var(--cream)]"
                    >
                      <td className="py-2">{row.word}</td>
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
            title={editingId === null ? t("newKeyword") : draft.word}
            pending={keywords.save.isPending}
            error={keywords.save.error ?? keywords.remove.error}
            submitLabel={canEdit ? stock("save") : null}
            onSubmit={() =>
              keywords.save.mutate(
                { id: editingId, body: { word: draft.word.trim(), vertical: draft.vertical } },
                { onSuccess: close },
              )
            }
            onDelete={
              canEdit && editingId !== null
                ? () => keywords.remove.mutate(editingId, { onSuccess: close })
                : null
            }
            deletePending={keywords.remove.isPending}
            headerAction={null}
            below={null}
          >
            <Field label={t("word")}>
              <Input
                required
                value={draft.word}
                onChange={(event) => setDraft({ ...draft, word: event.target.value })}
              />
            </Field>
          </EditorDialog>
        ) : null}
      </div>
    </LeadsShell>
  );
}
