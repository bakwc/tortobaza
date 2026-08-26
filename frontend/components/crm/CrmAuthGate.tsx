"use client";

import { useState, type FormEvent, type ReactNode } from "react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { ApiError } from "@/lib/api/client";
import { isUnauthenticatedError, useCurrentUser, useLogin } from "@/hooks/useAuth";

function extractDetail(error: ApiError, fallback: string): string {
  const parsed = error.parsed<Record<string, unknown>>();
  if (parsed && typeof parsed === "object") {
    const nonField = parsed["non_field_errors"];
    if (Array.isArray(nonField) && typeof nonField[0] === "string") {
      return nonField[0];
    }
    const detail = parsed["detail"];
    if (typeof detail === "string") {
      return detail;
    }
  }
  return fallback;
}

function LoginForm() {
  const t = useTranslations("crm");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const login = useLogin();

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    login.mutate({ username, password });
  };

  const errorMessage =
    login.error instanceof ApiError
      ? extractDetail(login.error, t("invalidCredentials"))
      : login.error
        ? t("genericError")
        : null;

  return (
    <div className="mx-auto max-w-md rounded-3xl border border-[var(--line)] bg-white p-8 shadow-sm">
      <h1 className="text-2xl font-semibold text-[var(--ink)]">{t("signInTitle")}</h1>
      <p className="mt-1 text-sm text-[var(--muted-2)]">{t("signInSubtitle")}</p>

      <form className="mt-6 grid gap-4" onSubmit={onSubmit}>
        <label className="flex flex-col gap-1.5">
          <span className="text-xs font-medium uppercase tracking-wide text-[var(--ink)]/60">
            {t("username")}
          </span>
          <Input
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            autoComplete="username"
            autoFocus
          />
        </label>
        <label className="flex flex-col gap-1.5">
          <span className="text-xs font-medium uppercase tracking-wide text-[var(--ink)]/60">
            {t("password")}
          </span>
          <Input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete="current-password"
          />
        </label>

        {errorMessage ? (
          <p className="text-sm text-[var(--danger)]">{errorMessage}</p>
        ) : null}

        <Button type="submit" size="lg" disabled={login.isPending || !username || !password}>
          {login.isPending ? <Spinner className="h-4 w-4" /> : t("signIn")}
        </Button>
      </form>
    </div>
  );
}

export function CrmAuthGate({ children }: { children: ReactNode }) {
  const t = useTranslations("crm");
  const currentUser = useCurrentUser();

  if (currentUser.isLoading) {
    return (
      <div className="mx-auto flex min-h-[60vh] max-w-md items-center justify-center px-4">
        <Spinner className="h-6 w-6 text-[var(--brand)]" />
      </div>
    );
  }

  if (currentUser.isError && !isUnauthenticatedError(currentUser.error)) {
    return (
      <div className="mx-auto max-w-md px-4 py-16 text-center text-sm text-[var(--danger)]">
        {t("serverUnreachable")}
      </div>
    );
  }

  if (!currentUser.data) {
    return <LoginForm />;
  }

  return children;
}
