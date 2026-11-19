"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { EditorDialog } from "@/components/menu/EditorDialog";
import { Card, CardTitle, CheckboxField, Field, NativeSelect, QueryState } from "@/components/menu/ui";
import { useCan } from "@/hooks/useAuth";
import { useEmployees } from "@/hooks/useEmployees";
import { useGroups } from "@/hooks/useGroups";
import type { Employee, EmployeeBody } from "@/lib/api/types";

function emptyDraft(): EmployeeBody {
  return {
    username: "",
    password: "",
    first_name: "",
    last_name: "",
    email: "",
    is_active: true,
    is_staff: false,
    hourly_rate: "0.00",
    monthly_rate: "0.00",
    can_login: true,
    telegram_username: "",
    internal_name: "",
    gender: "female",
    groups: [],
    is_active_courier: false,
    bark_device_key: "",
    position: "",
    in_schedule: false,
    skip_late_alerts: false,
  };
}

function draftFrom(row: Employee): EmployeeBody {
  return {
    username: row.username,
    password: "",
    first_name: row.first_name,
    last_name: row.last_name,
    email: row.email,
    is_active: row.is_active,
    is_staff: row.is_staff,
    hourly_rate: row.hourly_rate,
    monthly_rate: row.monthly_rate,
    can_login: row.can_login,
    telegram_username: row.telegram_username,
    internal_name: row.internal_name,
    gender: row.gender,
    groups: row.groups,
    is_active_courier: row.is_active_courier,
    bark_device_key: row.bark_device_key,
    position: row.position,
    in_schedule: row.in_schedule,
    skip_late_alerts: row.skip_late_alerts,
  };
}

function displayName(row: { internal_name: string; username: string }): string {
  const internal = row.internal_name.trim();
  return internal || row.username;
}

type ActivityFilter = "active" | "inactive" | "all";

export function EmployeesPanel() {
  const t = useTranslations("employees");
  const section = useTranslations("crm");
  const canEdit = useCan("edit_employees");
  const employees = useEmployees();
  const groups = useGroups();
  const [editingId, setEditingId] = useState<number | null>(null);
  const [draft, setDraft] = useState<EmployeeBody | null>(null);
  const [activity, setActivity] = useState<ActivityFilter>("active");

  const open = (row: Employee | null) => {
    employees.save.reset();
    setEditingId(row ? row.id : null);
    setDraft(row ? draftFrom(row) : emptyDraft());
  };

  const close = () => setDraft(null);

  const flag = (value: boolean) => (value ? t("yes") : t("no"));
  const rows = (employees.list.data ?? []).filter((row) => {
    if (activity === "active") return row.is_active;
    if (activity === "inactive") return !row.is_active;
    return true;
  });
  const filters: { key: ActivityFilter; label: string }[] = [
    { key: "active", label: t("filterActive") },
    { key: "inactive", label: t("filterInactive") },
    { key: "all", label: t("filterAll") },
  ];

  return (
    <div className="grid gap-6">
      <Card>
        <div className="flex items-center justify-between gap-3">
          <CardTitle>{section("employeesSection")}</CardTitle>
          {canEdit ? (
          <Button type="button" size="sm" onClick={() => open(null)}>
            <Plus className="mr-1 h-4 w-4" />
            {t("add")}
          </Button>
          ) : null}
        </div>
        <div className="mt-4 inline-flex rounded-full border border-[var(--line)] bg-white p-0.5">
          {filters.map((item) => (
            <button
              key={item.key}
              type="button"
              onClick={() => setActivity(item.key)}
              className={`rounded-full px-3 py-1 text-xs font-medium ${
                item.key === activity
                  ? "bg-[var(--brand)] text-[var(--brand-foreground)]"
                  : "text-[var(--ink)]"
              }`}
            >
              {item.label}
            </button>
          ))}
        </div>
        <QueryState isLoading={employees.list.isLoading} isError={employees.list.isError}>
          <div className="mt-4 overflow-x-auto">
            <table className="w-full min-w-[56rem] text-sm">
              <thead className="text-left text-xs uppercase tracking-wide text-[var(--ink)]/50">
                <tr>
                  <th className="py-2 pr-3">{t("name")}</th>
                  <th className="py-2 pr-3">{t("position")}</th>
                  <th className="py-2 pr-3">{t("username")}</th>
                  <th className="py-2 pr-3">{t("hourlyRate")}</th>
                  <th className="py-2 pr-3">{t("monthlyRate")}</th>
                  <th className="py-2 pr-3">{t("canLogin")}</th>
                  <th className="py-2 pr-3">{t("groups")}</th>
                  <th className="py-2 pr-3">{t("courier")}</th>
                  <th className="py-2 pr-3">{t("staff")}</th>
                  <th className="py-2">{t("active")}</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr
                    key={row.id}
                    onClick={() => open(row)}
                    className="cursor-pointer border-t border-[var(--line)] hover:bg-[var(--cream)]"
                  >
                    <td className="py-2 pr-3">
                      <span className="inline-flex items-center gap-2">
                        {displayName(row)}
                        {row.is_staff ? (
                          <span className="rounded-full bg-[var(--brand)]/15 px-2 py-0.5 text-xs text-[var(--brand)]">
                            {t("staff")}
                          </span>
                        ) : null}
                        {!row.is_active ? (
                          <span className="rounded-full bg-[var(--cream)] px-2 py-0.5 text-xs text-[var(--muted)]">
                            {t("inactive")}
                          </span>
                        ) : null}
                      </span>
                    </td>
                    <td className="py-2 pr-3">{row.position}</td>
                    <td className="py-2 pr-3">{row.username}</td>
                    <td className="py-2 pr-3 tabular-nums">{row.hourly_rate}</td>
                    <td className="py-2 pr-3 tabular-nums">{row.monthly_rate}</td>
                    <td className="py-2 pr-3">{flag(row.can_login)}</td>
                    <td className="py-2 pr-3">
                      {(groups.list.data ?? [])
                        .filter((group) => row.groups.includes(group.id))
                        .map((group) => group.name)
                        .join(", ")}
                    </td>
                    <td className="py-2 pr-3">{flag(row.is_active_courier)}</td>
                    <td className="py-2 pr-3">{flag(row.is_staff)}</td>
                    <td className="py-2">{flag(row.is_active)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </QueryState>
      </Card>
      {draft !== null ? (
        <EditorDialog
          open
          onOpenChange={(value) => (value ? null : close())}
          onCancel={null}
          title={editingId === null ? t("newEmployee") : displayName(draft)}
          pending={employees.save.isPending}
          error={employees.save.error}
          submitLabel={canEdit ? t("save") : null}
          onSubmit={() =>
            employees.save.mutate(
              {
                id: editingId,
                body: {
                  username: draft.username.trim(),
                  password: draft.password,
                  first_name: draft.first_name.trim(),
                  last_name: draft.last_name.trim(),
                  email: draft.email.trim(),
                  is_active: draft.is_active,
                  is_staff: draft.is_staff,
                  hourly_rate: draft.hourly_rate.trim(),
                  monthly_rate: draft.monthly_rate.trim(),
                  can_login: draft.can_login,
                  telegram_username: draft.telegram_username.trim(),
                  internal_name: draft.internal_name.trim(),
                  gender: draft.gender,
                  groups: draft.groups,
                  is_active_courier: draft.is_active_courier,
                  bark_device_key: draft.bark_device_key.trim(),
                  position: draft.position.trim(),
                  in_schedule: draft.in_schedule,
                  skip_late_alerts: draft.skip_late_alerts,
                },
              },
              { onSuccess: close },
            )
          }
          onDelete={null}
          deletePending={false}
          headerAction={null}
          below={null}
        >
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label={t("username")}>
              <Input required value={draft.username} onChange={(event) => setDraft({ ...draft, username: event.target.value })} />
            </Field>
            <Field label={t("password")}>
              <Input
                type="password"
                required={editingId === null}
                value={draft.password}
                autoComplete="new-password"
                placeholder={editingId === null ? undefined : t("passwordHint")}
                onChange={(event) => setDraft({ ...draft, password: event.target.value })}
              />
            </Field>
            <Field label={t("firstName")}>
              <Input value={draft.first_name} onChange={(event) => setDraft({ ...draft, first_name: event.target.value })} />
            </Field>
            <Field label={t("lastName")}>
              <Input value={draft.last_name} onChange={(event) => setDraft({ ...draft, last_name: event.target.value })} />
            </Field>
            <Field label={t("email")} className="sm:col-span-2">
              <Input type="email" value={draft.email} onChange={(event) => setDraft({ ...draft, email: event.target.value })} />
            </Field>
            <Field label={t("internalName")}>
              <Input value={draft.internal_name} onChange={(event) => setDraft({ ...draft, internal_name: event.target.value })} />
            </Field>
            <Field label={t("position")}>
              <Input value={draft.position} onChange={(event) => setDraft({ ...draft, position: event.target.value })} />
            </Field>
            <Field label={t("telegram")}>
              <Input value={draft.telegram_username} onChange={(event) => setDraft({ ...draft, telegram_username: event.target.value })} />
            </Field>
            <Field label={t("hourlyRate")}>
              <Input required value={draft.hourly_rate} onChange={(event) => setDraft({ ...draft, hourly_rate: event.target.value })} />
            </Field>
            <Field label={t("monthlyRate")}>
              <Input required value={draft.monthly_rate} onChange={(event) => setDraft({ ...draft, monthly_rate: event.target.value })} />
            </Field>
            <Field label={t("gender")}>
              <NativeSelect
                value={draft.gender}
                onChange={(event) =>
                  setDraft({ ...draft, gender: event.target.value === "male" ? "male" : "female" })
                }
              >
                <option value="female">{t("genderFemale")}</option>
                <option value="male">{t("genderMale")}</option>
              </NativeSelect>
            </Field>
            <Field label={t("bark")}>
              <Input value={draft.bark_device_key} onChange={(event) => setDraft({ ...draft, bark_device_key: event.target.value })} />
            </Field>
            <div className="grid gap-3 sm:col-span-2 sm:grid-cols-2">
              <CheckboxField label={t("canLogin")} checked={draft.can_login} onChange={(value) => setDraft({ ...draft, can_login: value })} />
              <div className="grid gap-2 sm:col-span-2">
                <p className="text-sm font-semibold text-[var(--ink)]">{t("groups")}</p>
                {(groups.list.data ?? []).map((group) => (
                  <CheckboxField
                    key={group.id}
                    label={group.name}
                    checked={draft.groups.includes(group.id)}
                    onChange={(value) =>
                      setDraft({
                        ...draft,
                        groups: value
                          ? [...draft.groups, group.id]
                          : draft.groups.filter((id) => id !== group.id),
                      })
                    }
                  />
                ))}
              </div>
              <CheckboxField
                label={t("courier")}
                checked={draft.is_active_courier}
                onChange={(value) => setDraft({ ...draft, is_active_courier: value })}
              />
              <CheckboxField label={t("staff")} checked={draft.is_staff} onChange={(value) => setDraft({ ...draft, is_staff: value })} />
              <CheckboxField label={t("active")} checked={draft.is_active} onChange={(value) => setDraft({ ...draft, is_active: value })} />
              <CheckboxField
                label={t("inSchedule")}
                checked={draft.in_schedule}
                onChange={(value) => setDraft({ ...draft, in_schedule: value })}
              />
              <CheckboxField
                label={t("skipLateAlerts")}
                checked={draft.skip_late_alerts}
                onChange={(value) => setDraft({ ...draft, skip_late_alerts: value })}
              />
            </div>
          </div>
        </EditorDialog>
      ) : null}
    </div>
  );
}
