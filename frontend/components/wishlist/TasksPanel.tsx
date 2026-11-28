"use client";

import { useMemo, useState, type ReactNode } from "react";
import { DndContext, PointerSensor, useDraggable, useDroppable, useSensor, useSensors, type DragEndEvent } from "@dnd-kit/core";
import { useTranslations } from "next-intl";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { EditorDialog } from "@/components/menu/EditorDialog";
import { Card, CardTitle, CheckboxField, Field, NativeSelect, QueryState } from "@/components/menu/ui";
import { WishlistShell } from "@/components/wishlist/WishlistShell";
import { useCan } from "@/hooks/useAuth";
import { useTasks } from "@/hooks/useTasks";
import { cn } from "@/lib/utils";
import type { Task, TaskBody, TaskStatus } from "@/lib/api/types";

const STATUSES = ["todo", "in_progress", "done"] as const;

const STATUS_LABEL = {
  todo: "statusTodo",
  in_progress: "statusInProgress",
  done: "statusDone",
} as const;

type Draft = {
  title: string;
  description: string;
  status: TaskStatus;
  assignee: string;
};

function draftFrom(row: Task | null): Draft {
  if (row === null) {
    return { title: "", description: "", status: "todo", assignee: "" };
  }
  return {
    title: row.title,
    description: row.description,
    status: row.status,
    assignee: String(row.assignee),
  };
}

function bodyFrom(draft: Draft): TaskBody {
  return {
    title: draft.title.trim(),
    description: draft.description.trim(),
    status: draft.status,
    assignee: Number(draft.assignee),
  };
}

function isStatus(value: string): value is TaskStatus {
  return value === "todo" || value === "in_progress" || value === "done";
}

function TaskCard({ task, canDrag, onOpen }: { task: Task; canDrag: boolean; onOpen: () => void }) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: task.id,
    disabled: !canDrag,
  });
  const style = transform === null ? undefined : { transform: `translate3d(${transform.x}px, ${transform.y}px, 0)` };
  return (
    <div
      ref={setNodeRef}
      style={style}
      {...listeners}
      {...attributes}
      onClick={onOpen}
      className={cn(
        "cursor-pointer rounded-xl border border-[var(--line)] bg-white px-3 py-2 text-left shadow-sm",
        isDragging && "opacity-60",
      )}
    >
      <div className="text-sm font-medium">{task.title}</div>
      <div className="mt-1 text-xs text-[var(--ink)]/50">{task.author_name}</div>
    </div>
  );
}

function StatusCell({ id, children }: { id: string; children: ReactNode }) {
  const { setNodeRef, isOver } = useDroppable({ id });
  return (
    <div
      ref={setNodeRef}
      className={cn(
        "flex min-h-28 flex-col gap-2 rounded-2xl border border-dashed border-[var(--line)] p-2",
        isOver && "border-[var(--brand)] bg-[var(--cream-soft)]",
      )}
    >
      {children}
    </div>
  );
}

export function TasksPanel() {
  const t = useTranslations("wishlist");
  const stock = useTranslations("stock");
  const canEdit = useCan("edit_wishlist");
  const [hideOldDone, setHideOldDone] = useState(true);
  const items = useTasks(hideOldDone);
  const rows = items.list.data ?? [];
  const assignees = items.assignees.data ?? [];
  const [editingId, setEditingId] = useState<number | null>(null);
  const [draft, setDraft] = useState<Draft | null>(null);
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 8 } }));
  const editing = rows.find((row) => row.id === editingId) ?? null;
  const groups = useMemo(() => {
    const byAssignee = new Map<number, Task[]>();
    for (const row of rows) {
      const current = byAssignee.get(row.assignee) ?? [];
      current.push(row);
      byAssignee.set(row.assignee, current);
    }
    return [...byAssignee.entries()]
      .map(([assignee, tasks]) => ({ assignee, name: tasks[0].assignee_name, tasks }))
      .sort((left, right) => left.name.localeCompare(right.name, "ru"));
  }, [rows]);

  const open = (row: Task | null) => {
    items.save.reset();
    items.remove.reset();
    setEditingId(row === null ? null : row.id);
    setDraft(draftFrom(row));
  };

  const close = () => setDraft(null);

  const onDragEnd = (event: DragEndEvent) => {
    if (!canEdit || event.over === null) return;
    const task = rows.find((row) => row.id === event.active.id);
    if (task === undefined) return;
    const [assigneeText, status] = String(event.over.id).split(":");
    if (Number(assigneeText) !== task.assignee || !isStatus(status) || status === task.status) return;
    items.save.mutate({
      id: task.id,
      body: {
        title: task.title,
        description: task.description,
        status,
        assignee: task.assignee,
      },
    });
  };

  return (
    <WishlistShell section="tasks">
      <Card>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <CardTitle>{t("tasks")}</CardTitle>
          <div className="flex flex-wrap items-center gap-4">
            <CheckboxField label={t("hideOldDone")} checked={hideOldDone} onChange={setHideOldDone} />
            {canEdit ? (
              <Button type="button" size="sm" onClick={() => open(null)}>
                <Plus className="mr-1 h-4 w-4" />
                {t("add")}
              </Button>
            ) : null}
          </div>
        </div>
        <QueryState isLoading={items.list.isLoading} isError={items.list.isError}>
          {groups.length === 0 ? (
            <p className="mt-4 text-sm text-[var(--muted-2)]">{t("empty")}</p>
          ) : (
            <DndContext sensors={sensors} onDragEnd={onDragEnd}>
              <div className="mt-4 overflow-x-auto">
                <div className="grid min-w-[720px] grid-cols-3 gap-3">
                  {STATUSES.map((status) => (
                    <div key={status} className="px-1 text-xs font-semibold uppercase tracking-wide text-[var(--ink)]/50">
                      {t(STATUS_LABEL[status])}
                    </div>
                  ))}
                  {groups.map((group) => (
                    <div key={group.assignee} className="col-span-3 grid grid-cols-3 gap-3">
                      <div className="col-span-3 flex items-center gap-3 border-y border-[var(--line)] bg-[var(--cream)] px-3 py-2">
                        <span className="text-sm font-semibold">{group.name}</span>
                        <span className="text-xs text-[var(--ink)]/50">{group.tasks.length}</span>
                      </div>
                      {STATUSES.map((status) => (
                        <StatusCell key={status} id={`${group.assignee}:${status}`}>
                          {group.tasks
                            .filter((task) => task.status === status)
                            .map((task) => (
                              <TaskCard key={task.id} task={task} canDrag={canEdit} onOpen={() => open(task)} />
                            ))}
                        </StatusCell>
                      ))}
                    </div>
                  ))}
                </div>
              </div>
            </DndContext>
          )}
        </QueryState>
      </Card>
      {draft !== null ? (
        <EditorDialog
          open
          onOpenChange={(value) => (value ? null : close())}
          onCancel={null}
          title={editingId === null ? t("newTask") : draft.title}
          pending={items.save.isPending}
          error={items.save.error ?? items.remove.error}
          submitLabel={canEdit ? stock("save") : null}
          onSubmit={() => items.save.mutate({ id: editingId, body: bodyFrom(draft) }, { onSuccess: close })}
          onDelete={
            canEdit && editingId !== null ? () => items.remove.mutate(editingId, { onSuccess: close }) : null
          }
          deletePending={items.remove.isPending}
          headerAction={null}
          below={null}
        >
          <div className="grid gap-4">
            <Field label={t("taskTitle")}>
              <Input
                required
                value={draft.title}
                onChange={(event) => setDraft({ ...draft, title: event.target.value })}
              />
            </Field>
            <Field label={t("taskDescription")}>
              <Textarea
                value={draft.description}
                onChange={(event) => setDraft({ ...draft, description: event.target.value })}
              />
            </Field>
            <Field label={t("assignee")}>
              <NativeSelect
                required
                value={draft.assignee}
                onChange={(event) => setDraft({ ...draft, assignee: event.target.value })}
              >
                <option value="" />
                {assignees.map((person) => (
                  <option key={person.id} value={person.id}>
                    {person.name}
                  </option>
                ))}
              </NativeSelect>
            </Field>
            <Field label={t("status")}>
              <NativeSelect
                required
                value={draft.status}
                onChange={(event) => setDraft({ ...draft, status: event.target.value as TaskStatus })}
              >
                {STATUSES.map((status) => (
                  <option key={status} value={status}>
                    {t(STATUS_LABEL[status])}
                  </option>
                ))}
              </NativeSelect>
            </Field>
            {editing !== null ? (
              <Field label={t("author")}>
                <Input readOnly value={editing.author_name} />
              </Field>
            ) : null}
          </div>
        </EditorDialog>
      ) : null}
    </WishlistShell>
  );
}
