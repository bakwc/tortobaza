import type { CrmOrderStatus } from "@/lib/api/types";

export const CRM_ORDER_STATUSES = [
  "new",
  "in_work",
  "client_approved",
  "in_delivery",
  "delivered",
] as const;

export const CRM_ORDER_STATUS_MESSAGE_KEYS = {
  new: "statusNew",
  in_work: "statusInWork",
  client_approved: "statusClientApproved",
  in_delivery: "statusInDelivery",
  delivered: "statusDelivered",
} as const;

export const CRM_CLIENT_ORDER_STATUS_MESSAGE_KEYS = {
  new: "clientStatusNew",
  in_work: "clientStatusInWork",
  client_approved: "clientStatusClientApproved",
  in_delivery: "clientStatusInDelivery",
  delivered: "clientStatusDelivered",
} as const;

export const CRM_ORDER_NEXT_STATUS = {
  new: "in_work",
  in_work: "client_approved",
  client_approved: "in_delivery",
  in_delivery: "delivered",
  delivered: null,
} as const satisfies Record<CrmOrderStatus, CrmOrderStatus | null>;

export const CRM_ORDER_NEXT_STEP_MESSAGE_KEYS = {
  in_work: "takeInWork",
  client_approved: "nextStepClientApproved",
  in_delivery: "nextStepInDelivery",
  delivered: "nextStepDelivered",
} as const;

type CrmOrderStatusTone = {
  card: string;
  media: string;
  panel: string;
  panelSoft: string;
  divider: string;
  chip: string;
};

const TONES: Record<CrmOrderStatus, CrmOrderStatusTone> = {
  new: {
    card: "border-[var(--line)] bg-white",
    media: "border-[var(--line)] bg-[var(--cream)]",
    panel: "border-[var(--line)]",
    panelSoft: "bg-[var(--cream-soft)]",
    divider: "border-[var(--line)]",
    chip: "bg-[var(--cream)] text-[var(--ink)]",
  },
  in_work: {
    card: "border-orange-300 bg-orange-100",
    media: "border-orange-200 bg-white",
    panel: "border-orange-200/80 bg-white/70",
    panelSoft: "border border-orange-200/80 bg-white/80",
    divider: "border-orange-200",
    chip: "bg-orange-600 text-white",
  },
  client_approved: {
    card: "border-emerald-300 bg-emerald-100",
    media: "border-emerald-200 bg-white",
    panel: "border-emerald-200/80 bg-white/70",
    panelSoft: "border border-emerald-200/80 bg-white/80",
    divider: "border-emerald-200",
    chip: "bg-emerald-600 text-white",
  },
  in_delivery: {
    card: "border-violet-300 bg-violet-100",
    media: "border-violet-200 bg-white",
    panel: "border-violet-200/80 bg-white/70",
    panelSoft: "border border-violet-200/80 bg-white/80",
    divider: "border-violet-200",
    chip: "bg-violet-600 text-white",
  },
  delivered: {
    card: "border-sky-300 bg-sky-100",
    media: "border-sky-200 bg-white",
    panel: "border-sky-200/80 bg-white/70",
    panelSoft: "border border-sky-200/80 bg-white/80",
    divider: "border-sky-200",
    chip: "bg-sky-600 text-white",
  },
};

export function crmOrderStatusTone(status: CrmOrderStatus): CrmOrderStatusTone {
  return TONES[status];
}
