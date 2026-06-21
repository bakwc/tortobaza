"use client";

import { useState, type FormEvent } from "react";
import { LogOut } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { ApiError } from "@/lib/api/client";
import { isUnauthenticatedError, useCurrentUser, useLogin, useLogout } from "@/hooks/useAuth";
import { useMarkAttendance } from "@/hooks/useAttendance";
import type { AttendanceEvent, AttendanceEventType, SessionUser } from "@/lib/api/types";

export default function AttendancePage() {
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
        Could not reach the server. Please try again.
      </div>
    );
  }

  return (
    <div className="mx-auto w-full max-w-md px-4 py-12">
      {currentUser.data ? (
        <AttendancePanel user={currentUser.data} />
      ) : (
        <LoginForm />
      )}
    </div>
  );
}

function LoginForm() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const login = useLogin();

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    login.mutate({ username, password });
  };

  const errorMessage =
    login.error instanceof ApiError
      ? extractDetail(login.error)
      : login.error
        ? "Something went wrong. Please try again."
        : null;

  return (
    <div className="rounded-3xl border border-[var(--line)] bg-white p-8 shadow-sm">
      <h1 className="text-2xl font-semibold text-[var(--ink)]">Staff sign in</h1>
      <p className="mt-1 text-sm text-[var(--muted-2)]">Sign in to mark your attendance.</p>

      <form className="mt-6 grid gap-4" onSubmit={onSubmit}>
        <label className="flex flex-col gap-1.5">
          <span className="text-xs font-medium uppercase tracking-wide text-[var(--ink)]/60">
            Username
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
            Password
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
          {login.isPending ? <Spinner className="h-4 w-4" /> : "Sign in"}
        </Button>
      </form>
    </div>
  );
}

function AttendancePanel({ user }: { user: SessionUser }) {
  const logout = useLogout();
  const mark = useMarkAttendance();
  const [lastEvent, setLastEvent] = useState<AttendanceEvent | null>(null);

  const displayName =
    [user.first_name, user.last_name].filter(Boolean).join(" ") || user.username;

  const onMark = (eventType: AttendanceEventType) => {
    mark.mutate(eventType, {
      onSuccess: (event) => setLastEvent(event),
    });
  };

  return (
    <div className="rounded-3xl border border-[var(--line)] bg-white p-8 shadow-sm">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-[var(--ink)]/60">
            Signed in as
          </p>
          <h1 className="text-2xl font-semibold text-[var(--ink)]">{displayName}</h1>
        </div>
        <Button
          variant="ghost"
          size="icon"
          onClick={() => logout.mutate()}
          disabled={logout.isPending}
          aria-label="Sign out"
          title="Sign out"
        >
          <LogOut className="h-5 w-5" />
        </Button>
      </div>

      <div className="mt-8 grid gap-3">
        <Button
          size="lg"
          className="h-16 text-base"
          onClick={() => onMark("arrival")}
          disabled={mark.isPending}
        >
          {mark.isPending && mark.variables === "arrival" ? (
            <Spinner className="h-5 w-5" />
          ) : (
            "Mark arrival"
          )}
        </Button>
        <Button
          variant="outline"
          size="lg"
          className="h-16 text-base"
          onClick={() => onMark("departure")}
          disabled={mark.isPending}
        >
          {mark.isPending && mark.variables === "departure" ? (
            <Spinner className="h-5 w-5" />
          ) : (
            "Mark departure"
          )}
        </Button>
      </div>

      {lastEvent ? (
        <p className="mt-6 text-center text-sm text-[var(--ink)]/70">
          {lastEvent.event_type === "arrival" ? "Arrival" : "Departure"} marked at{" "}
          {new Date(lastEvent.timestamp).toLocaleString()}
        </p>
      ) : null}

      {mark.isError ? (
        <p className="mt-6 text-center text-sm text-[var(--danger)]">
          Could not mark attendance. Please try again.
        </p>
      ) : null}
    </div>
  );
}

function extractDetail(error: ApiError): string {
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
  return "Invalid username or password.";
}
