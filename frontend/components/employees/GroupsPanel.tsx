"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { EditorDialog } from "@/components/menu/EditorDialog";
import { Card, CardTitle, CheckboxField, Field, QueryState } from "@/components/menu/ui";
import { useCan } from "@/hooks/useAuth";
import { useGroups } from "@/hooks/useGroups";
import type { AccessGroup, AccessGroupBody, SectionPermissionOption } from "@/lib/api/types";

function emptyDraft(): AccessGroupBody {
  return { name: "", permissions: [] };
}

function draftFrom(row: AccessGroup): AccessGroupBody {
  return { name: row.name, permissions: row.permissions };
}

function sectionKey(code: string): string {
  return code.replace(/^(view|edit)_/, "");
}

function grouped(options: SectionPermissionOption[]): { key: string; codes: SectionPermissionOption[] }[] {
  const sections: { key: string; codes: SectionPermissionOption[] }[] = [];
  for (const option of options) {
    const key = sectionKey(option.code);
    const found = sections.find((section) => section.key === key);
    if (found) found.codes.push(option);
    else sections.push({ key, codes: [option] });
  }
  return sections;
}

export function GroupsPanel() {
  const t = useTranslations("employees");
  const section = useTranslations("crm");
  const canEdit = useCan("edit_employees");
  const groups = useGroups();
  const [editingId, setEditingId] = useState<number | null>(null);
  const [draft, setDraft] = useState<AccessGroupBody | null>(null);

  const open = (row: AccessGroup | null) => {
    groups.save.reset();
    groups.remove.reset();
    setEditingId(row ? row.id : null);
    setDraft(row ? draftFrom(row) : emptyDraft());
  };

  const close = () => setDraft(null);

  const toggle = (code: string, on: boolean) => {
    if (draft === null) return;
    setDraft({
      ...draft,
      permissions: on ? [...draft.permissions, code] : draft.permissions.filter((item) => item !== code),
    });
  };

  const sections = grouped(groups.permissions.data ?? []);

  return (
    <div className="grid gap-6">
      <Card>
        <div className="flex items-center justify-between gap-3">
          <CardTitle>{section("groupsSection")}</CardTitle>
          {canEdit ? (
            <Button type="button" size="sm" onClick={() => open(null)}>
              <Plus className="mr-1 h-4 w-4" />
              {t("add")}
            </Button>
          ) : null}
        </div>
        <QueryState
          isLoading={groups.list.isLoading || groups.permissions.isLoading}
          isError={groups.list.isError || groups.permissions.isError}
        >
          <div className="mt-4 grid gap-2">
            {(groups.list.data ?? []).map((row) => (
              <button
                key={row.id}
                type="button"
                onClick={() => open(row)}
                className="flex items-center justify-between gap-3 rounded-2xl border border-[var(--line)] px-4 py-3 text-left hover:bg-[var(--cream)]"
              >
                <span className="font-medium text-[var(--ink)]">{row.name}</span>
                <span className="text-sm text-[var(--muted-2)]">{row.permissions.length}</span>
              </button>
            ))}
          </div>
        </QueryState>
      </Card>
      {draft !== null ? (
        <EditorDialog
          open
          onOpenChange={(value) => (value ? null : close())}
          onCancel={null}
          title={editingId === null ? t("newGroup") : draft.name}
          pending={groups.save.isPending}
          error={groups.save.error ?? groups.remove.error}
          submitLabel={canEdit ? t("save") : null}
          onSubmit={() =>
            groups.save.mutate(
              { id: editingId, body: { name: draft.name.trim(), permissions: draft.permissions } },
              { onSuccess: close },
            )
          }
          onDelete={
            canEdit && editingId !== null
              ? () => groups.remove.mutate(editingId, { onSuccess: close })
              : null
          }
          deletePending={groups.remove.isPending}
          headerAction={null}
          below={null}
        >
          <div className="grid gap-5">
            <Field label={t("groupName")}>
              <Input
                required
                value={draft.name}
                onChange={(event) => setDraft({ ...draft, name: event.target.value })}
              />
            </Field>
            {sections.map((block) => (
              <div key={block.key} className="grid gap-2">
                <p className="text-sm font-semibold text-[var(--ink)]">{t(`section_${block.key}`)}</p>
                <div className="grid gap-2 sm:grid-cols-2">
                  {block.codes.map((option) => (
                    <CheckboxField
                      key={option.code}
                      label={t(`perm_${option.code}`)}
                      checked={draft.permissions.includes(option.code)}
                      onChange={(value) => toggle(option.code, value)}
                    />
                  ))}
                </div>
              </div>
            ))}
          </div>
        </EditorDialog>
      ) : null}
    </div>
  );
}
