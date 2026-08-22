"use client";

import { useState, type FormEvent } from "react";
import * as VisuallyHidden from "@radix-ui/react-visually-hidden";
import {
  Calendar,
  Check,
  ChevronLeft,
  ChevronRight,
  Clock,
  CreditCard,
  FileText,
  LogOut,
  Package,
  Store,
  Truck,
  User,
  ZoomIn,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { ApiError } from "@/lib/api/client";
import { isUnauthenticatedError, useCurrentUser, useLogin, useLogout } from "@/hooks/useAuth";
import { useCrmOrders, usePatchCrmOrder } from "@/hooks/useCrmOrders";
import type { CrmOrder, SessionUser } from "@/lib/api/types";
import { formatAed, formatCrmDate, getTbilisiTodayIsoDate } from "@/lib/format";
import { cn } from "@/lib/utils";

function shiftDate(isoDate: string, days: number): string {
  const [yearStr, monthStr, dayStr] = isoDate.split("-");
  const year = Number(yearStr);
  const month = Number(monthStr);
  const day = Number(dayStr);
  const date = new Date(Date.UTC(year, month - 1, day));
  date.setUTCDate(date.getUTCDate() + days);
  const nextYear = date.getUTCFullYear();
  const nextMonth = String(date.getUTCMonth() + 1).padStart(2, "0");
  const nextDay = String(date.getUTCDate()).padStart(2, "0");
  return `${nextYear}-${nextMonth}-${nextDay}`;
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

export default function CrmPage() {
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
    <div className="mx-auto w-full max-w-5xl px-4 py-8 md:py-12">
      {currentUser.data ? <CrmBoard user={currentUser.data} /> : <LoginForm />}
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
    <div className="mx-auto max-w-md rounded-3xl border border-[var(--line)] bg-white p-8 shadow-sm">
      <h1 className="text-2xl font-semibold text-[var(--ink)]">Staff Sign In</h1>
      <p className="mt-1 text-sm text-[var(--muted-2)]">Sign in to access the CRM order board.</p>

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
          {login.isPending ? <Spinner className="h-4 w-4" /> : "Sign In"}
        </Button>
      </form>
    </div>
  );
}

function CrmBoard({ user }: { user: SessionUser }) {
  const logout = useLogout();
  const todayStr = getTbilisiTodayIsoDate();
  const [selectedDate, setSelectedDate] = useState<string>(todayStr);

  const ordersQuery = useCrmOrders(selectedDate);
  const patchMutation = usePatchCrmOrder();

  const displayName =
    [user.first_name, user.last_name].filter(Boolean).join(" ") || user.username;

  const orders = ordersQuery.data?.orders ?? [];
  const isToday = selectedDate === todayStr;

  const deliveredCount = orders.filter((o) => o.is_delivered).length;
  const paidCount = orders.filter((o) => o.is_paid).length;

  return (
    <div className="grid gap-6">
      <div className="flex flex-col gap-4 rounded-3xl border border-[var(--line)] bg-white p-6 shadow-sm sm:flex-row sm:items-center sm:justify-between">
        <div>
          <span className="text-xs font-medium uppercase tracking-wider text-[var(--brand)]">
            CRM Order Board
          </span>
          <h1 className="text-2xl font-bold text-[var(--ink)]">Daily Orders</h1>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-right">
            <span className="text-xs text-[var(--muted-2)]">Signed in as</span>
            <p className="text-sm font-semibold text-[var(--ink)]">{displayName}</p>
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
      </div>

      <div className="rounded-3xl border border-[var(--line)] bg-white p-6 shadow-sm">
        <div className="flex flex-col items-center justify-between gap-4 sm:flex-row">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setSelectedDate((prev) => shiftDate(prev, -1))}
            className="flex items-center gap-1.5"
          >
            <ChevronLeft className="h-4 w-4" />
            <span>Previous Day</span>
          </Button>

          <div className="flex flex-col items-center gap-1 text-center">
            <div className="flex items-center gap-2">
              <Calendar className="h-5 w-5 text-[var(--brand)]" />
              <h2 className="text-lg font-bold text-[var(--ink)]">
                {formatCrmDate(selectedDate)}
              </h2>
            </div>
            <div className="flex items-center gap-2">
              {isToday ? (
                <span className="rounded-full bg-[var(--brand)]/15 px-2.5 py-0.5 text-xs font-semibold text-[var(--brand)]">
                  Today
                </span>
              ) : (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setSelectedDate(todayStr)}
                  className="h-7 text-xs font-medium text-[var(--brand)] hover:text-[var(--brand)]"
                >
                  Jump to Today
                </Button>
              )}
            </div>
          </div>

          <Button
            variant="outline"
            size="sm"
            onClick={() => setSelectedDate((prev) => shiftDate(prev, 1))}
            className="flex items-center gap-1.5"
          >
            <span>Next Day</span>
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>

        <div className="mt-6 flex flex-wrap items-center justify-center gap-3 border-t border-[var(--line)] pt-4 text-xs sm:gap-6 sm:text-sm">
          <div className="flex items-center gap-1.5 text-[var(--ink)]">
            <Package className="h-4 w-4 text-[var(--muted-2)]" />
            <span>Total:</span>
            <span className="font-bold">{orders.length}</span>
          </div>
          <div className="flex items-center gap-1.5 text-emerald-700">
            <Check className="h-4 w-4" />
            <span>Delivered:</span>
            <span className="font-bold">
              {deliveredCount} / {orders.length}
            </span>
          </div>
          <div className="flex items-center gap-1.5 text-[var(--brand)]">
            <CreditCard className="h-4 w-4" />
            <span>Paid:</span>
            <span className="font-bold">
              {paidCount} / {orders.length}
            </span>
          </div>
        </div>
      </div>

      {ordersQuery.isLoading ? (
        <div className="flex min-h-[300px] items-center justify-center rounded-3xl border border-[var(--line)] bg-white p-12">
          <Spinner className="h-8 w-8 text-[var(--brand)]" />
        </div>
      ) : ordersQuery.isError ? (
        <div className="rounded-3xl border border-[var(--line)] bg-white p-12 text-center text-sm text-[var(--danger)]">
          Could not load orders for this date. Please try again.
        </div>
      ) : orders.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-3xl border border-[var(--line)] bg-white p-12 text-center">
          <Package className="h-12 w-12 text-[var(--muted)]" />
          <p className="mt-4 text-base font-semibold text-[var(--ink)]">
            No orders scheduled for this day
          </p>
          <p className="mt-1 text-sm text-[var(--muted-2)]">
            Use the arrows above to browse other days.
          </p>
        </div>
      ) : (
        <div className="grid gap-6">
          {orders.map((order) => (
            <CrmOrderCard
              key={order.id}
              order={order}
              isPatching={patchMutation.isPending && patchMutation.variables?.id === order.id}
              onToggleDelivered={() =>
                patchMutation.mutate({
                  id: order.id,
                  body: { is_delivered: !order.is_delivered },
                })
              }
              onTogglePaid={() =>
                patchMutation.mutate({
                  id: order.id,
                  body: { is_paid: !order.is_paid },
                })
              }
            />
          ))}
        </div>
      )}
    </div>
  );
}

function formatTimeSlot(start: string, end: string | null): string {
  const s = start.slice(0, 5);
  if (!end) return s;
  return `${s} – ${end.slice(0, 5)}`;
}

function paymentTypeLabel(type: string): string {
  if (type === "cash") return "Cash";
  if (type === "terminal") return "Terminal";
  if (type === "tbc") return "TBC Transfer";
  if (type === "bog") return "BOG Transfer";
  return type;
}

function CrmOrderCard({
  order,
  isPatching,
  onToggleDelivered,
  onTogglePaid,
}: {
  order: CrmOrder;
  isPatching: boolean;
  onToggleDelivered: () => void;
  onTogglePaid: () => void;
}) {
  const [activeImageIndex, setActiveImageIndex] = useState<number>(0);
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);

  const images = order.images;
  const activeImage = images[activeImageIndex] ?? images[0];

  const priceNum = Number.parseFloat(order.cake_price);
  const prepayNum = Number.parseFloat(order.prepayment);
  const remainingNum = Math.max(0, priceNum - prepayNum);

  return (
    <div className="rounded-3xl border border-[var(--line)] bg-white p-6 shadow-sm md:p-8">
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12 lg:gap-8">
        <div className="flex flex-col gap-3 lg:col-span-5">
          <div className="relative aspect-square w-full overflow-hidden rounded-2xl border border-[var(--line)] bg-[var(--cream)]">
            {activeImage ? (
              <button
                type="button"
                onClick={() => setIsModalOpen(true)}
                className="group relative h-full w-full cursor-pointer focus:outline-none"
                title="Click to enlarge"
              >
                <img
                  src={activeImage.image.src}
                  srcSet={activeImage.image.srcset}
                  sizes="(max-width: 1024px) 100vw, 40vw"
                  alt={`Order #${order.id}`}
                  className="h-full w-full object-contain transition-transform duration-200 group-hover:scale-[1.02]"
                  loading="lazy"
                />
                <span className="absolute bottom-3 right-3 flex h-8 w-8 items-center justify-center rounded-full bg-black/60 text-white opacity-0 transition-opacity duration-200 group-hover:opacity-100">
                  <ZoomIn className="h-4 w-4" />
                </span>
              </button>
            ) : (
              <div className="flex h-full w-full flex-col items-center justify-center gap-2 text-[var(--muted-2)]">
                <Package className="h-10 w-10 text-[var(--muted)]" />
                <span className="text-sm">No image</span>
              </div>
            )}
          </div>

          {images.length > 1 ? (
            <div className="flex flex-wrap gap-2">
              {images.map((img, idx) => (
                <button
                  type="button"
                  key={img.id}
                  onClick={() => setActiveImageIndex(idx)}
                  className={cn(
                    "relative h-16 w-16 overflow-hidden rounded-xl border-2 bg-[var(--cream)] transition-all",
                    activeImageIndex === idx
                      ? "border-[var(--brand)] ring-2 ring-[var(--brand)]/30"
                      : "border-[var(--line)] opacity-70 hover:opacity-100",
                  )}
                >
                  <img
                    src={img.image.src}
                    srcSet={img.image.srcset}
                    sizes="64px"
                    alt={`Thumb ${idx + 1}`}
                    className="h-full w-full object-contain"
                  />
                </button>
              ))}
            </div>
          ) : null}

          {activeImage ? (
            <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
              <DialogContent className="max-w-4xl p-4 md:p-6">
                <VisuallyHidden.Root asChild>
                  <DialogTitle>Order #{order.id} Image</DialogTitle>
                </VisuallyHidden.Root>
                <div className="flex flex-col items-center gap-4">
                  <div className="relative flex max-h-[75vh] w-full items-center justify-center overflow-hidden rounded-2xl bg-[var(--cream)] p-2">
                    <img
                      src={activeImage.image.src}
                      srcSet={activeImage.image.srcset}
                      sizes="(max-width: 1024px) 95vw, 80vw"
                      alt={`Order #${order.id}`}
                      className="max-h-[72vh] w-auto max-w-full object-contain"
                    />
                  </div>
                  {images.length > 1 ? (
                    <div className="flex flex-wrap justify-center gap-2">
                      {images.map((img, idx) => (
                        <button
                          type="button"
                          key={img.id}
                          onClick={() => setActiveImageIndex(idx)}
                          className={cn(
                            "relative h-16 w-16 overflow-hidden rounded-xl border-2 bg-[var(--cream)] transition-all",
                            activeImageIndex === idx
                              ? "border-[var(--brand)] ring-2 ring-[var(--brand)]/30"
                              : "border-[var(--line)] opacity-70 hover:opacity-100",
                          )}
                        >
                          <img
                            src={img.image.src}
                            srcSet={img.image.srcset}
                            sizes="64px"
                            alt={`Thumb ${idx + 1}`}
                            className="h-full w-full object-contain"
                          />
                        </button>
                      ))}
                    </div>
                  ) : null}
                </div>
              </DialogContent>
            </Dialog>
          ) : null}
        </div>

        <div className="flex flex-col justify-between gap-6 lg:col-span-7">
          <div className="flex flex-col gap-4">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--line)] pb-4">
              <div className="flex items-center gap-2">
                <Clock className="h-5 w-5 text-[var(--brand)]" />
                <span className="text-2xl font-bold tracking-tight text-[var(--ink)]">
                  {formatTimeSlot(order.time_start, order.time_end)}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span
                  className={cn(
                    "flex items-center gap-1 rounded-full px-3 py-1 text-xs font-semibold",
                    order.fulfillment_type === "delivery"
                      ? "bg-amber-100 text-amber-900"
                      : "bg-blue-100 text-blue-900",
                  )}
                >
                  {order.fulfillment_type === "delivery" ? (
                    <>
                      <Truck className="h-3.5 w-3.5" />
                      <span>Delivery</span>
                    </>
                  ) : (
                    <>
                      <Store className="h-3.5 w-3.5" />
                      <span>Pickup</span>
                    </>
                  )}
                </span>
                <span className="rounded-full bg-[var(--cream)] px-2.5 py-1 text-xs font-medium text-[var(--ink)]">
                  #{order.id}
                </span>
              </div>
            </div>

            <div className="rounded-2xl bg-[var(--cream-soft)] p-4 text-sm text-[var(--ink)]">
              <div className="flex items-start gap-2">
                <User className="mt-0.5 h-4 w-4 shrink-0 text-[var(--brand)]" />
                <div>
                  <span className="font-semibold text-xs uppercase tracking-wider text-[var(--ink)]/60">
                    Contact & Address
                  </span>
                  <p className="mt-1 whitespace-pre-wrap font-medium">{order.contact}</p>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div className="rounded-2xl border border-[var(--line)] p-3.5">
                <span className="text-xs font-medium uppercase tracking-wider text-[var(--muted-2)]">
                  Weight
                </span>
                <p className="mt-1 font-semibold text-[var(--ink)]">{order.weight}</p>
              </div>
              <div className="rounded-2xl border border-[var(--line)] p-3.5">
                <span className="text-xs font-medium uppercase tracking-wider text-[var(--muted-2)]">
                  Filling
                </span>
                <p className="mt-1 font-semibold text-[var(--ink)]">{order.filling}</p>
              </div>
            </div>

            {order.description ? (
              <div className="rounded-2xl border border-[var(--line)] p-3.5">
                <div className="flex items-center gap-1.5 text-xs font-medium uppercase tracking-wider text-[var(--muted-2)]">
                  <FileText className="h-3.5 w-3.5" />
                  <span>Notes / Description</span>
                </div>
                <p className="mt-1 whitespace-pre-wrap text-sm text-[var(--ink)]">
                  {order.description}
                </p>
              </div>
            ) : null}

            <div className="grid grid-cols-2 gap-3 rounded-2xl bg-[var(--cream-soft)] p-4 sm:grid-cols-4">
              <div>
                <span className="text-xs text-[var(--muted-2)]">Price</span>
                <p className="mt-0.5 text-base font-bold text-[var(--ink)]">
                  {formatAed(order.cake_price)}
                </p>
              </div>
              <div>
                <span className="text-xs text-[var(--muted-2)]">Prepaid</span>
                <p className="mt-0.5 text-base font-semibold text-[var(--ink)]">
                  {formatAed(order.prepayment)}
                </p>
              </div>
              <div>
                <span className="text-xs text-[var(--muted-2)]">Remaining</span>
                <p
                  className={cn(
                    "mt-0.5 text-base font-bold",
                    remainingNum > 0 ? "text-[var(--danger)]" : "text-emerald-700",
                  )}
                >
                  {formatAed(remainingNum)}
                </p>
              </div>
              <div>
                <span className="text-xs text-[var(--muted-2)]">Payment Method</span>
                <p className="mt-0.5 text-sm font-semibold text-[var(--ink)]">
                  {paymentTypeLabel(order.payment_type)}
                </p>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-3 pt-2 sm:grid-cols-2">
            <Button
              type="button"
              size="lg"
              onClick={onToggleDelivered}
              disabled={isPatching}
              className={cn(
                "h-14 font-semibold transition-all",
                order.is_delivered
                  ? "bg-emerald-600 text-white hover:bg-emerald-700"
                  : "border-2 border-[var(--line)] bg-white text-[var(--ink)] hover:bg-[var(--cream-soft)]",
              )}
            >
              {isPatching ? (
                <Spinner className="h-5 w-5" />
              ) : order.is_delivered ? (
                <span className="flex items-center gap-2">
                  <Check className="h-5 w-5" />
                  Delivered
                </span>
              ) : (
                <span className="flex items-center gap-2">
                  <Truck className="h-5 w-5 text-[var(--muted-2)]" />
                  Mark Delivered
                </span>
              )}
            </Button>

            <Button
              type="button"
              size="lg"
              onClick={onTogglePaid}
              disabled={isPatching}
              className={cn(
                "h-14 font-semibold transition-all",
                order.is_paid
                  ? "bg-emerald-600 text-white hover:bg-emerald-700"
                  : "border-2 border-[var(--line)] bg-white text-[var(--ink)] hover:bg-[var(--cream-soft)]",
              )}
            >
              {isPatching ? (
                <Spinner className="h-5 w-5" />
              ) : order.is_paid ? (
                <span className="flex items-center gap-2">
                  <Check className="h-5 w-5" />
                  Paid
                </span>
              ) : (
                <span className="flex items-center gap-2">
                  <CreditCard className="h-5 w-5 text-[var(--muted-2)]" />
                  Mark Paid
                </span>
              )}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
