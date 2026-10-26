"use client";

import { useState, type FormEvent } from "react";
import { useTranslations } from "next-intl";
import { ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Spinner } from "@/components/ui/spinner";
import { Textarea } from "@/components/ui/textarea";
import { CrmOrderItemsEditor } from "@/components/crm/CrmOrderItemsEditor";
import { CrmPaymentLinkField } from "@/components/crm/CrmPaymentLinkField";
import { ImageBatchUploader } from "@/components/crm/ImageBatchUploader";
import { MondayDatePicker } from "@/components/crm/MondayDatePicker";
import { apiErrorMessage } from "@/components/menu/ui";
import { Link, useRouter } from "@/i18n/navigation";
import { useCreateCrmOrder, useUpdateCrmOrder } from "@/hooks/useCrmOrders";
import { useTechCards } from "@/hooks/useStock";
import { ApiError } from "@/lib/api/client";
import type {
  CrmOrder,
  CrmOrderItemBody,
  CrmOrderPaymentType,
  CrmOrderStatus,
  CrmOrderWriteFields,
} from "@/lib/api/types";
import {
  crmItemBody,
  crmItemDraftFromItem,
  crmItemsFillingText,
  crmItemsPriceSum,
  crmItemsWeightText,
  type CrmItemDraft,
} from "@/lib/crmItems";
import {
  CRM_ORDER_STATUS_MESSAGE_KEYS,
  CRM_ORDER_STATUSES,
  crmOrderSelectableStatuses,
} from "@/lib/crmStatus";
import { cn } from "@/lib/utils";

function sliceTime(value: string): string {
  return value.slice(0, 5);
}

function timeToMinutes(value: string): number {
  const [hours, minutes] = value.split(":").map(Number);
  return hours * 60 + minutes;
}

function buildCrmOrderFormData(
  fields: CrmOrderWriteFields,
  images: File[],
  deleteImageIds: number[],
  items: CrmOrderItemBody[],
): FormData {
  const form = new FormData();
  form.append("items", JSON.stringify(items));
  form.append("date", fields.date);
  form.append("time_start", fields.time_start ?? "");
  form.append("time_end", fields.time_end ?? "");
  form.append("when_ready", fields.when_ready ? "true" : "false");
  form.append("contact", fields.contact);
  form.append("is_gift", fields.is_gift ? "true" : "false");
  form.append("nickname", fields.nickname);
  form.append("delivery_address", fields.delivery_address);
  form.append("fulfillment_type", fields.fulfillment_type);
  form.append("status", fields.status);
  form.append("weight", fields.weight);
  form.append("filling", fields.filling);
  form.append("description", fields.description);
  form.append("internal_description", fields.internal_description);
  form.append("cake_price", fields.cake_price);
  form.append("delivery_price", fields.delivery_price);
  form.append("prepayment", fields.prepayment);
  form.append("is_paid", fields.is_paid ? "true" : "false");
  form.append("payment_type", fields.payment_type);
  form.append("payment_date", fields.payment_date ?? "");
  for (const file of images) {
    form.append("images", file);
  }
  for (const id of deleteImageIds) {
    form.append("delete_image_ids", String(id));
  }
  return form;
}

function fieldsFromOrder(order: CrmOrder): CrmOrderWriteFields {
  return {
    date: order.date,
    time_start: order.time_start ? sliceTime(order.time_start) : null,
    time_end: order.time_end ? sliceTime(order.time_end) : null,
    when_ready: order.when_ready,
    contact: order.contact,
    is_gift: order.is_gift,
    nickname: order.nickname,
    delivery_address: order.delivery_address,
    fulfillment_type: order.fulfillment_type,
    status: order.status,
    weight: order.weight,
    filling: order.filling,
    description: order.description,
    internal_description: order.internal_description,
    cake_price: order.cake_price,
    delivery_price: order.delivery_price,
    prepayment: order.prepayment,
    is_paid: order.is_paid,
    payment_type: order.payment_type,
    payment_date: order.payment_date,
  };
}

function emptyFields(initialDate: string): CrmOrderWriteFields {
  return {
    date: initialDate,
    time_start: "",
    time_end: null,
    when_ready: false,
    contact: "",
    is_gift: false,
    nickname: "",
    delivery_address: "",
    fulfillment_type: "delivery",
    status: "new",
    weight: "",
    filling: "",
    description: "",
    internal_description: "",
    cake_price: "",
    delivery_price: "0",
    prepayment: "0",
    is_paid: false,
    payment_type: "unknown",
    payment_date: null,
  };
}

export function CrmOrderForm(
  props: { mode: "create"; initialDate: string } | { mode: "edit"; order: CrmOrder },
) {
  const t = useTranslations("crm");
  const router = useRouter();
  const createMutation = useCreateCrmOrder();
  const updateMutation = useUpdateCrmOrder();
  const [fields, setFields] = useState<CrmOrderWriteFields>(() =>
    props.mode === "edit" ? fieldsFromOrder(props.order) : emptyFields(props.initialDate),
  );
  const [existingImages, setExistingImages] = useState(
    props.mode === "edit"
      ? props.order.images.map((img) => ({
          id: img.id,
          src: img.image.src,
          srcset: img.image.srcset,
        }))
      : [],
  );
  const [deleteImageIds, setDeleteImageIds] = useState<number[]>([]);
  const [newFiles, setNewFiles] = useState<File[]>([]);
  const [items, setItems] = useState<CrmItemDraft[]>(() =>
    props.mode === "edit" ? props.order.items.map(crmItemDraftFromItem) : [],
  );
  const [weightTouched, setWeightTouched] = useState(props.mode === "edit" && props.order.weight !== "");
  const [fillingTouched, setFillingTouched] = useState(props.mode === "edit" && props.order.filling !== "");
  const techCards = useTechCards();
  const cards = techCards.list.data ?? [];
  const itemsPriceSum = crmItemsPriceSum(items);
  const priceMismatch =
    itemsPriceSum !== null && Math.abs(itemsPriceSum - Number(fields.cake_price.replace(",", ".") || "0")) >= 0.01;
  const foodCost = props.mode === "edit" ? props.order.food_cost : undefined;

  const onItemsChange = (next: CrmItemDraft[]) => {
    setItems(next);
    const weightText = crmItemsWeightText(next, cards, { kg: t("items.kg"), pcs: t("items.pcs") });
    const fillingText = next.length === 0 ? "" : crmItemsFillingText(next, cards);
    setFields((prev) => ({
      ...prev,
      weight: !weightTouched ? weightText : prev.weight,
      filling: !fillingTouched && fillingText !== "" ? fillingText : prev.filling,
    }));
  };
  const [timeRangeError, setTimeRangeError] = useState<"timeEndRequired" | "timeRangeMin20" | null>(
    null,
  );

  const selectableStatuses =
    props.mode === "edit"
      ? crmOrderSelectableStatuses(props.order.status)
      : CRM_ORDER_STATUSES;

  const pending = createMutation.isPending || updateMutation.isPending;
  const mutationError = createMutation.error ?? updateMutation.error;
  const errorMessage =
    mutationError instanceof ApiError
      ? apiErrorMessage(mutationError, t("saveError"))
      : mutationError
        ? t("genericError")
        : null;

  const setField = <K extends keyof CrmOrderWriteFields>(
    key: K,
    value: CrmOrderWriteFields[K],
  ) => {
    if (key === "time_start" || key === "time_end") {
      setTimeRangeError(null);
    }
    setFields((prev) => ({ ...prev, [key]: value }));
  };

  const clearTimeFlags = () => {
    setTimeRangeError(null);
    setFields((prev) => {
      if (!prev.when_ready && prev.time_start !== null) {
        return prev;
      }
      return {
        ...prev,
        time_start: prev.time_start ?? "",
        when_ready: false,
      };
    });
  };

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!fields.when_ready && fields.time_start !== null) {
      if (!fields.time_end) {
        setTimeRangeError("timeEndRequired");
        return;
      }
      if (timeToMinutes(fields.time_end) - timeToMinutes(fields.time_start) < 20) {
        setTimeRangeError("timeRangeMin20");
        return;
      }
    }
    const body = buildCrmOrderFormData(
      fields,
      newFiles,
      deleteImageIds,
      items.map((item) => crmItemBody(item, cards)),
    );
    if (props.mode === "create") {
      createMutation.mutate(body, {
        onSuccess: (order) => {
          router.push(`/crm?date=${order.date}`);
        },
      });
      return;
    }
    updateMutation.mutate(
      { id: props.order.id, body },
      {
        onSuccess: (order) => {
          router.push(`/crm?date=${order.date}`);
        },
      },
    );
  };

  const paymentOptions: { value: CrmOrderPaymentType; label: string }[] = [
    { value: "unknown", label: t("paymentUnknown") },
    { value: "cash", label: t("paymentCash") },
    { value: "terminal", label: t("paymentTerminal") },
    { value: "tbc", label: t("paymentTbc") },
    { value: "bog", label: t("paymentBog") },
    { value: "tbank", label: t("paymentTbank") },
    { value: "flowwow", label: t("paymentFlowwow") },
    { value: "crypto", label: t("paymentCrypto") },
    { value: "paypal", label: t("paymentPaypal") },
    { value: "online", label: t("paymentOnline") },
  ];

  return (
    <form className="grid gap-6" onSubmit={onSubmit}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Link
          href={`/crm?date=${fields.date}`}
          className="inline-flex items-center gap-1.5 text-sm font-medium text-[var(--muted-2)] hover:text-[var(--ink)]"
        >
          <ArrowLeft className="h-4 w-4" />
          {t("formBack")}
        </Link>
        <h1 className="text-2xl font-semibold text-[var(--ink)]">
          {props.mode === "create" ? t("formCreateTitle") : t("formEditTitle")}
        </h1>
      </div>

      <section className="rounded-3xl border border-[var(--line)] bg-white p-6 shadow-sm">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-[var(--ink)]/50">
          {t("scheduleSection")}
        </h2>
        <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <label className="flex flex-col gap-1.5 sm:col-span-2 lg:col-span-4">
            <span className="text-xs font-medium uppercase tracking-wide text-[var(--ink)]/60">
              {t("dateLabel")}
            </span>
            <MondayDatePicker value={fields.date} onChange={(iso) => setField("date", iso)} />
          </label>
          <label className="flex flex-col gap-1.5">
            <span className="text-xs font-medium uppercase tracking-wide text-[var(--ink)]/60">
              {t("timeStart")}
            </span>
            <Input
              type="time"
              required={fields.time_start !== null && !fields.when_ready}
              value={fields.time_start ?? ""}
              onPointerDown={clearTimeFlags}
              onFocus={clearTimeFlags}
              onChange={(event) => {
                setTimeRangeError(null);
                setFields((prev) => ({
                  ...prev,
                  time_start: event.target.value,
                  when_ready: false,
                }));
              }}
              className="rounded-2xl"
            />
          </label>
          <label className="flex flex-col gap-1.5">
            <span className="text-xs font-medium uppercase tracking-wide text-[var(--ink)]/60">
              {t("timeEnd")}
            </span>
            <Input
              type="time"
              value={fields.time_end ?? ""}
              onPointerDown={clearTimeFlags}
              onFocus={clearTimeFlags}
              onChange={(event) => {
                setTimeRangeError(null);
                const value = event.target.value === "" ? null : event.target.value;
                setFields((prev) => ({
                  ...prev,
                  time_start: prev.time_start ?? "",
                  time_end: value,
                  when_ready: false,
                }));
              }}
              className="rounded-2xl"
            />
          </label>
          <div className="flex flex-col gap-1.5">
            <span className="text-xs font-medium uppercase tracking-wide text-[var(--ink)]/60">
              &nbsp;
            </span>
            <button
              type="button"
              onClick={() => {
                setTimeRangeError(null);
                if (fields.time_start === null && !fields.when_ready) {
                  setFields((prev) => ({ ...prev, time_start: "", when_ready: false }));
                  return;
                }
                setFields((prev) => ({
                  ...prev,
                  time_start: null,
                  time_end: null,
                  when_ready: false,
                }));
              }}
              className={cn(
                "flex h-12 cursor-pointer items-center justify-center rounded-2xl border px-4 text-sm",
                fields.time_start === null && !fields.when_ready
                  ? "border-[var(--brand)] bg-[var(--cream)]"
                  : "border-[var(--line)] bg-white",
              )}
            >
              {t("timeUnknown")}
            </button>
          </div>
          <div className="flex flex-col gap-1.5">
            <span className="text-xs font-medium uppercase tracking-wide text-[var(--ink)]/60">
              &nbsp;
            </span>
            <button
              type="button"
              onClick={() => {
                setTimeRangeError(null);
                if (fields.when_ready) {
                  setFields((prev) => ({ ...prev, time_start: "", when_ready: false }));
                  return;
                }
                setFields((prev) => ({
                  ...prev,
                  time_start: null,
                  time_end: null,
                  when_ready: true,
                }));
              }}
              className={cn(
                "flex h-12 cursor-pointer items-center justify-center rounded-2xl border px-4 text-sm",
                fields.when_ready
                  ? "border-[var(--brand)] bg-[var(--cream)]"
                  : "border-[var(--line)] bg-white",
              )}
            >
              {t("timeWhenReady")}
            </button>
          </div>
        </div>
      </section>

      <section className="rounded-3xl border border-[var(--line)] bg-white p-6 shadow-sm">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-[var(--ink)]/50">
          {t("customerSection")}
        </h2>
        <div className="mt-4 grid gap-4">
          <div className="flex items-end gap-3">
            <label className="flex min-w-0 flex-1 flex-col gap-1.5">
              <span className="text-xs font-medium uppercase tracking-wide text-[var(--ink)]/60">
                {t("contact")}
              </span>
              <Textarea
                required
                value={fields.contact}
                onChange={(event) => setField("contact", event.target.value)}
                className={fields.is_gift ? "border-red-200 bg-red-100" : undefined}
              />
            </label>
            <label className="flex h-12 shrink-0 cursor-pointer items-center gap-2 rounded-2xl border border-[var(--line)] px-4 text-sm">
              <input
                type="checkbox"
                checked={fields.is_gift}
                onChange={(event) => setField("is_gift", event.target.checked)}
                className="h-4 w-4 accent-[var(--brand)]"
              />
              {t("gift")}
            </label>
          </div>
          <label className="flex flex-col gap-1.5">
            <span className="text-xs font-medium uppercase tracking-wide text-[var(--ink)]/60">
              {t("nickname")}
            </span>
            <Input
              value={fields.nickname}
              onChange={(event) => setField("nickname", event.target.value)}
            />
          </label>
          <label className="flex flex-col gap-1.5">
            <span className="text-xs font-medium uppercase tracking-wide text-[var(--ink)]/60">
              {t("deliveryAddress")}
            </span>
            <Textarea
              value={fields.delivery_address}
              onChange={(event) => setField("delivery_address", event.target.value)}
            />
          </label>
          <div className="flex flex-col gap-1.5">
            <span className="text-xs font-medium uppercase tracking-wide text-[var(--ink)]/60">
              {t("fulfillmentLabel")}
            </span>
            <RadioGroup
              value={fields.fulfillment_type}
              onValueChange={(value) =>
                setField("fulfillment_type", value as "delivery" | "pickup")
              }
              className="grid grid-cols-2 gap-2 sm:max-w-md"
            >
              <label
                className={cn(
                  "flex cursor-pointer items-center gap-2 rounded-2xl border px-4 py-3 text-sm",
                  fields.fulfillment_type === "delivery"
                    ? "border-[var(--brand)] bg-[var(--cream)]"
                    : "border-[var(--line)]",
                )}
              >
                <RadioGroupItem value="delivery" />
                {t("delivery")}
              </label>
              <label
                className={cn(
                  "flex cursor-pointer items-center gap-2 rounded-2xl border px-4 py-3 text-sm",
                  fields.fulfillment_type === "pickup"
                    ? "border-[var(--brand)] bg-[var(--cream)]"
                    : "border-[var(--line)]",
                )}
              >
                <RadioGroupItem value="pickup" />
                {t("pickup")}
              </label>
            </RadioGroup>
          </div>
        </div>
      </section>

      <section className="rounded-3xl border border-[var(--line)] bg-white p-6 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-[var(--ink)]/50">
            {t("items.section")}
          </h2>
          {foodCost !== undefined ? (
            <span className="text-sm font-medium text-[var(--ink)]">
              {t("items.foodCost", { value: Number(foodCost).toFixed(2) })}
            </span>
          ) : null}
        </div>
        <div className="mt-4">
          <CrmOrderItemsEditor items={items} onChange={onItemsChange} />
        </div>
      </section>

      <section className="rounded-3xl border border-[var(--line)] bg-white p-6 shadow-sm">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-[var(--ink)]/50">
          {t("cakeSection")}
        </h2>
        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <label className="flex flex-col gap-1.5">
            <span className="text-xs font-medium uppercase tracking-wide text-[var(--ink)]/60">
              {t("weight")}
            </span>
            <Input
              required
              value={fields.weight}
              onChange={(event) => {
                setWeightTouched(true);
                setField("weight", event.target.value);
              }}
            />
          </label>
          <label className="flex flex-col gap-1.5">
            <span className="text-xs font-medium uppercase tracking-wide text-[var(--ink)]/60">
              {t("filling")}
            </span>
            <Input
              required
              value={fields.filling}
              onChange={(event) => {
                setFillingTouched(true);
                setField("filling", event.target.value);
              }}
            />
          </label>
          <label className="flex flex-col gap-1.5 sm:col-span-2">
            <span className="text-xs font-medium uppercase tracking-wide text-[var(--ink)]/60">
              {t("notes")}
            </span>
            <Textarea
              value={fields.description}
              onChange={(event) => setField("description", event.target.value)}
            />
          </label>
          <label className="flex flex-col gap-1.5 sm:col-span-2">
            <span className="text-xs font-medium uppercase tracking-wide text-[var(--ink)]/60">
              {t("internalNotes")}
            </span>
            <Textarea
              value={fields.internal_description}
              onChange={(event) => setField("internal_description", event.target.value)}
            />
          </label>
        </div>
      </section>

      <section className="rounded-3xl border border-[var(--line)] bg-white p-6 shadow-sm">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-[var(--ink)]/50">
          {t("paymentSection")}
        </h2>
        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <label className="flex flex-col gap-1.5">
            <span className="text-xs font-medium uppercase tracking-wide text-[var(--ink)]/60">
              {t("priceWithoutDelivery")}
            </span>
            <Input
              required
              inputMode="decimal"
              value={fields.cake_price}
              onChange={(event) => setField("cake_price", event.target.value)}
            />
            {itemsPriceSum !== null ? (
              <span
                className={cn(
                  "text-xs",
                  priceMismatch ? "font-semibold text-amber-700" : "text-[var(--muted-2)]",
                )}
              >
                {t("items.priceSum", { value: itemsPriceSum.toFixed(2) })}
              </span>
            ) : null}
          </label>
          <label className="flex flex-col gap-1.5">
            <span className="text-xs font-medium uppercase tracking-wide text-[var(--ink)]/60">
              {t("delivery")}
            </span>
            <Input
              required
              inputMode="decimal"
              value={fields.delivery_price}
              onChange={(event) => setField("delivery_price", event.target.value)}
            />
          </label>
          <label className="flex flex-col gap-1.5">
            <span className="text-xs font-medium uppercase tracking-wide text-[var(--ink)]/60">
              {t("prepaid")}
            </span>
            <Input
              required
              inputMode="decimal"
              value={fields.prepayment}
              onChange={(event) => setField("prepayment", event.target.value)}
            />
          </label>
          <div className="flex flex-col gap-1.5 sm:col-span-2">
            <span className="text-xs font-medium uppercase tracking-wide text-[var(--ink)]/60">
              {t("paymentMethod")}
            </span>
            <RadioGroup
              value={fields.payment_type}
              onValueChange={(value) =>
                setField("payment_type", value as CrmOrderPaymentType)
              }
              className="grid grid-cols-2 gap-2 sm:grid-cols-3"
            >
              {paymentOptions.map((option) => (
                <label
                  key={option.value}
                  className={cn(
                    "flex cursor-pointer items-center gap-2 rounded-2xl border px-3 py-3 text-sm",
                    fields.payment_type === option.value
                      ? "border-[var(--brand)] bg-[var(--cream)]"
                      : "border-[var(--line)]",
                  )}
                >
                  <RadioGroupItem value={option.value} />
                  {option.label}
                </label>
              ))}
            </RadioGroup>
          </div>
          {props.mode === "edit" ? (
            <div className="sm:col-span-2">
              <CrmPaymentLinkField
                orderId={props.order.id}
                paymentUrl={props.order.payment_url}
                remaining={Math.max(
                  0,
                  Number(fields.cake_price) + Number(fields.delivery_price) - Number(fields.prepayment),
                )}
              />
            </div>
          ) : null}
          <label className="flex flex-col gap-1.5 sm:col-span-2">
            <span className="text-xs font-medium uppercase tracking-wide text-[var(--ink)]/60">
              {t("paymentDate")}
            </span>
            <Input
              type="date"
              value={fields.payment_date ?? ""}
              onChange={(event) =>
                setField("payment_date", event.target.value === "" ? null : event.target.value)
              }
            />
          </label>
          <div className="grid gap-2 sm:col-span-2 sm:grid-cols-2">
            <select
              value={fields.status}
              onChange={(event) => setField("status", event.target.value as CrmOrderStatus)}
              className="h-12 w-full rounded-full border border-[var(--line)] bg-white px-5 text-sm text-[var(--ink)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--brand)]/30"
            >
              {selectableStatuses.map((status) => (
                <option key={status} value={status}>
                  {t(CRM_ORDER_STATUS_MESSAGE_KEYS[status])}
                </option>
              ))}
            </select>
            <Button
              type="button"
              variant={fields.is_paid ? "primary" : "outline"}
              onClick={() => setField("is_paid", !fields.is_paid)}
            >
              {t("paid")}
            </Button>
          </div>
        </div>
      </section>

      <section className="rounded-3xl border border-[var(--line)] bg-white p-6 shadow-sm">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-[var(--ink)]/50">
          {t("imagesSection")}
        </h2>
        <div className="mt-4">
          <ImageBatchUploader
            existing={existingImages}
            newFiles={newFiles}
            onAddFiles={(files) => setNewFiles((prev) => [...prev, ...files])}
            onRemoveExisting={(id) => {
              setExistingImages((prev) => prev.filter((img) => img.id !== id));
              setDeleteImageIds((prev) => [...prev, id]);
            }}
            onRemoveNew={(index) => {
              setNewFiles((prev) => prev.filter((_, i) => i !== index));
            }}
          />
        </div>
      </section>

      {errorMessage ? <p className="text-sm text-[var(--danger)]">{errorMessage}</p> : null}

      <div className="flex flex-wrap justify-end gap-3 pb-8">
        <Button type="submit" size="lg" disabled={pending}>
          {pending ? <Spinner className="h-4 w-4" /> : t("saveOrder")}
        </Button>
      </div>

      <Dialog
        open={timeRangeError !== null}
        onOpenChange={(open) => {
          if (!open) {
            setTimeRangeError(null);
          }
        }}
      >
        <DialogContent className="w-[min(420px,calc(100vw-1.5rem))] max-w-[420px] p-6">
          <DialogTitle className="pr-10 text-lg font-semibold text-[var(--danger)]">
            {timeRangeError ? t(timeRangeError) : ""}
          </DialogTitle>
          <DialogDescription className="hidden">
            {timeRangeError ? t(timeRangeError) : ""}
          </DialogDescription>
        </DialogContent>
      </Dialog>
    </form>
  );
}
