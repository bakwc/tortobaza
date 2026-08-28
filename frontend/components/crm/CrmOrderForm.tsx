"use client";

import { useState, type FormEvent } from "react";
import { useTranslations } from "next-intl";
import { ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Spinner } from "@/components/ui/spinner";
import { Textarea } from "@/components/ui/textarea";
import { ImageBatchUploader } from "@/components/crm/ImageBatchUploader";
import { MondayDatePicker } from "@/components/crm/MondayDatePicker";
import { Link, useRouter } from "@/i18n/navigation";
import { useCreateCrmOrder, useUpdateCrmOrder } from "@/hooks/useCrmOrders";
import { ApiError } from "@/lib/api/client";
import type { CrmOrder, CrmOrderPaymentType, CrmOrderWriteFields } from "@/lib/api/types";
import { cn } from "@/lib/utils";

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

function sliceTime(value: string): string {
  return value.slice(0, 5);
}

function buildCrmOrderFormData(
  fields: CrmOrderWriteFields,
  images: File[],
  deleteImageIds: number[],
): FormData {
  const form = new FormData();
  form.append("date", fields.date);
  form.append("time_start", fields.time_start ?? "");
  form.append("time_end", fields.time_end ?? "");
  form.append("when_ready", fields.when_ready ? "true" : "false");
  form.append("contact", fields.contact);
  form.append("nickname", fields.nickname);
  form.append("delivery_address", fields.delivery_address);
  form.append("fulfillment_type", fields.fulfillment_type);
  form.append("is_delivered", fields.is_delivered ? "true" : "false");
  form.append("weight", fields.weight);
  form.append("filling", fields.filling);
  form.append("description", fields.description);
  form.append("cake_price", fields.cake_price);
  form.append("prepayment", fields.prepayment);
  form.append("is_paid", fields.is_paid ? "true" : "false");
  form.append("payment_type", fields.payment_type);
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
    nickname: order.nickname,
    delivery_address: order.delivery_address,
    fulfillment_type: order.fulfillment_type,
    is_delivered: order.is_delivered,
    weight: order.weight,
    filling: order.filling,
    description: order.description,
    cake_price: order.cake_price,
    prepayment: order.prepayment,
    is_paid: order.is_paid,
    payment_type: order.payment_type,
  };
}

function emptyFields(initialDate: string): CrmOrderWriteFields {
  return {
    date: initialDate,
    time_start: "",
    time_end: null,
    when_ready: false,
    contact: "",
    nickname: "",
    delivery_address: "",
    fulfillment_type: "delivery",
    is_delivered: false,
    weight: "",
    filling: "",
    description: "",
    cake_price: "",
    prepayment: "0",
    is_paid: false,
    payment_type: "unknown",
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

  const pending = createMutation.isPending || updateMutation.isPending;
  const mutationError = createMutation.error ?? updateMutation.error;
  const errorMessage =
    mutationError instanceof ApiError
      ? extractDetail(mutationError, t("saveError"))
      : mutationError
        ? t("genericError")
        : null;

  const setField = <K extends keyof CrmOrderWriteFields>(
    key: K,
    value: CrmOrderWriteFields[K],
  ) => {
    setFields((prev) => ({ ...prev, [key]: value }));
  };

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const body = buildCrmOrderFormData(fields, newFiles, deleteImageIds);
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
    { value: "flowwow", label: t("paymentFlowwow") },
    { value: "crypto", label: t("paymentCrypto") },
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
              disabled={fields.time_start === null || fields.when_ready}
              value={fields.time_start ?? ""}
              onChange={(event) => setField("time_start", event.target.value)}
              className="rounded-2xl"
            />
          </label>
          <label className="flex flex-col gap-1.5">
            <span className="text-xs font-medium uppercase tracking-wide text-[var(--ink)]/60">
              {t("timeEnd")}
            </span>
            <Input
              type="time"
              disabled={fields.time_start === null || fields.when_ready}
              value={fields.time_end ?? ""}
              onChange={(event) =>
                setField("time_end", event.target.value === "" ? null : event.target.value)
              }
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
          <label className="flex flex-col gap-1.5">
            <span className="text-xs font-medium uppercase tracking-wide text-[var(--ink)]/60">
              {t("contact")}
            </span>
            <Textarea
              required
              value={fields.contact}
              onChange={(event) => setField("contact", event.target.value)}
            />
          </label>
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
              onChange={(event) => setField("weight", event.target.value)}
            />
          </label>
          <label className="flex flex-col gap-1.5">
            <span className="text-xs font-medium uppercase tracking-wide text-[var(--ink)]/60">
              {t("filling")}
            </span>
            <Input
              required
              value={fields.filling}
              onChange={(event) => setField("filling", event.target.value)}
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
        </div>
      </section>

      <section className="rounded-3xl border border-[var(--line)] bg-white p-6 shadow-sm">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-[var(--ink)]/50">
          {t("paymentSection")}
        </h2>
        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <label className="flex flex-col gap-1.5">
            <span className="text-xs font-medium uppercase tracking-wide text-[var(--ink)]/60">
              {t("price")}
            </span>
            <Input
              required
              inputMode="decimal"
              value={fields.cake_price}
              onChange={(event) => setField("cake_price", event.target.value)}
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
          <div className="grid grid-cols-2 gap-2 sm:col-span-2">
            <Button
              type="button"
              variant={fields.is_delivered ? "primary" : "outline"}
              onClick={() => setField("is_delivered", !fields.is_delivered)}
            >
              {t("delivered")}
            </Button>
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
    </form>
  );
}
