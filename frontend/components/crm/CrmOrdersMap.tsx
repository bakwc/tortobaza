"use client";

import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { useTranslations } from "next-intl";
import { Clock, Home, Package } from "lucide-react";
import { Link } from "@/i18n/navigation";
import type { CrmMapOrder } from "@/lib/api/types";
import { crmOrderStatusTone } from "@/lib/crmStatus";
import {
  formatTimeSlot,
  minutesUntilTbilisiSlot,
  sortCrmBoardOrders,
} from "@/lib/format";
import {
  attachHtmlOverlay,
  googleMapsApi,
  loadGoogleMaps,
  type GoogleMapInstance,
} from "@/lib/google-maps";
import { SITE_INFO } from "@/lib/site-info";
import { cn } from "@/lib/utils";

const BATUMI = { lat: 41.6168, lng: 41.6367 };

function formatMapEta(
  minutes: number,
  labels: {
    now: string;
    overdue: (eta: string) => string;
    upcoming: (eta: string) => string;
    minutes: (value: number) => string;
    hours: (value: number) => string;
    hoursMinutes: (hours: number, minutes: number) => string;
  },
): string {
  if (minutes === 0) {
    return labels.now;
  }
  const abs = Math.abs(minutes);
  const hours = Math.floor(abs / 60);
  const mins = abs % 60;
  let eta = labels.minutes(abs);
  if (hours > 0 && mins === 0) {
    eta = labels.hours(hours);
  } else if (hours > 0) {
    eta = labels.hoursMinutes(hours, mins);
  }
  if (minutes < 0) {
    return labels.overdue(eta);
  }
  return labels.upcoming(eta);
}

function CrmMapOrderCard({ order }: { order: CrmMapOrder }) {
  const t = useTranslations("crm");
  const tone = crmOrderStatusTone(order.status);
  const [nowMs, setNowMs] = useState(() => Date.now());
  useEffect(() => {
    const id = window.setInterval(() => setNowMs(Date.now()), 60_000);
    return () => window.clearInterval(id);
  }, []);
  const slot = formatTimeSlot(
    order.time_start,
    order.time_end,
    order.when_ready,
    t("timeUnknown"),
    t("timeWhenReady"),
  );
  const timeStart = order.time_start;
  let etaMinutes: number | null = null;
  if (!order.when_ready && timeStart !== null && timeStart.slice(0, 5) !== "00:00") {
    etaMinutes = minutesUntilTbilisiSlot(order.date, timeStart, nowMs);
  }
  const countdown =
    etaMinutes === null
      ? null
      : formatMapEta(etaMinutes, {
          now: t("mapNow"),
          overdue: (eta) => t("mapEtaOverdue", { eta }),
          upcoming: (eta) => t("mapEtaIn", { eta }),
          minutes: (value) => t("mapMinutes", { minutes: value }),
          hours: (value) => t("mapHours", { hours: value }),
          hoursMinutes: (hours, minutes) => t("mapHoursMinutes", { hours, minutes }),
        });

  return (
    <Link
      href={`/crm?date=${order.date}&order=${order.id}`}
      className={cn(
        "relative flex w-[220px] gap-2 rounded-2xl border p-1.5 shadow-lg",
        tone.card,
      )}
    >
      <div
        className={cn(
          "h-12 w-12 shrink-0 overflow-hidden rounded-xl border",
          tone.media,
        )}
      >
        {order.image ? (
          <img
            src={order.image.src}
            srcSet={order.image.srcset}
            sizes="48px"
            alt={t("orderAlt", { id: order.id })}
            className="h-full w-full object-cover"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center text-[var(--muted)]">
            <Package className="h-4 w-4" />
          </div>
        )}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-1 text-[11px] font-semibold leading-tight text-[var(--ink)]">
          <Clock className="h-3 w-3 shrink-0 text-[var(--brand)]" />
          <span className="truncate">{slot}</span>
        </div>
        {countdown !== null && etaMinutes !== null ? (
          <p
            className={cn(
              "text-[10px] font-semibold leading-tight",
              etaMinutes < 0 ? "text-[var(--danger)]" : "text-[var(--brand)]",
            )}
          >
            {countdown}
          </p>
        ) : null}
        <p className="truncate text-[11px] leading-tight text-[var(--ink)]">
          <span className="font-semibold">{order.weight}</span>
          <span className="mx-1 text-[var(--muted-2)]">·</span>
          <span>{order.filling}</span>
        </p>
        {order.description ? (
          <p className="line-clamp-2 text-[10px] leading-tight text-[var(--muted-2)]">
            {order.description}
          </p>
        ) : null}
      </div>
      <span
        className={cn(
          "absolute -bottom-1.5 left-1/2 h-3 w-3 -translate-x-1/2 rotate-45 border-b border-r",
          tone.card,
        )}
      />
    </Link>
  );
}

function CrmMapOverlay({
  map,
  order,
}: {
  map: GoogleMapInstance;
  order: CrmMapOrder;
}) {
  const [host, setHost] = useState<HTMLDivElement | null>(null);

  useEffect(() => {
    const container = document.createElement("div");
    container.style.position = "absolute";
    container.style.transform = "translate(-50%, calc(-100% - 6px))";
    container.style.pointerEvents = "auto";
    container.style.zIndex = "1";
    setHost(container);
    const overlay = attachHtmlOverlay(
      googleMapsApi(),
      map,
      { lat: order.lat, lng: order.lng },
      container,
    );
    return () => {
      overlay.setMap(null);
    };
  }, [map, order.lat, order.lng]);

  if (!host) {
    return null;
  }
  return createPortal(<CrmMapOrderCard order={order} />, host);
}

function CrmMapBakeryCard() {
  const t = useTranslations("crm");
  return (
    <div className="relative flex w-[180px] items-center gap-2 rounded-2xl border border-[var(--line)] bg-[var(--cream)] p-1.5 shadow-lg">
      <span className="absolute -top-1.5 left-1/2 h-3 w-3 -translate-x-1/2 rotate-45 border-l border-t border-[var(--line)] bg-[var(--cream)]" />
      <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl border border-[var(--line)] bg-white text-[var(--brand)]">
        <Home className="h-5 w-5" />
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-[11px] font-semibold leading-tight text-[var(--ink)]">
          {SITE_INFO.brand}
        </p>
        <p className="truncate text-[10px] leading-tight text-[var(--muted-2)]">
          {t("mapBakery")}
        </p>
      </div>
    </div>
  );
}

function CrmMapBakeryOverlay({ map }: { map: GoogleMapInstance }) {
  const [host, setHost] = useState<HTMLDivElement | null>(null);

  useEffect(() => {
    const container = document.createElement("div");
    container.style.position = "absolute";
    container.style.transform = "translate(-50%, 8px)";
    container.style.pointerEvents = "none";
    container.style.zIndex = "0";
    setHost(container);
    const overlay = attachHtmlOverlay(
      googleMapsApi(),
      map,
      { lat: SITE_INFO.geo.latitude, lng: SITE_INFO.geo.longitude },
      container,
    );
    return () => {
      overlay.setMap(null);
    };
  }, [map]);

  if (!host) {
    return null;
  }
  return createPortal(<CrmMapBakeryCard />, host);
}

export function CrmOrdersMap({ orders }: { orders: CrmMapOrder[] }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [map, setMap] = useState<GoogleMapInstance | null>(null);
  const apiKey = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY;
  if (!apiKey) {
    throw new Error("NEXT_PUBLIC_GOOGLE_MAPS_API_KEY is not set");
  }

  useEffect(() => {
    const el = containerRef.current;
    if (!el) {
      return;
    }
    let cancelled = false;
    loadGoogleMaps(apiKey).then((maps) => {
      if (cancelled || !containerRef.current) {
        return;
      }
      const created = new maps.Map(containerRef.current, {
        center: BATUMI,
        zoom: 13,
        clickableIcons: false,
        mapTypeControl: false,
        streetViewControl: false,
        fullscreenControl: true,
        gestureHandling: "greedy",
        maxZoom: 17,
      });
      setMap(created);
    });
    return () => {
      cancelled = true;
    };
  }, [apiKey]);

  useEffect(() => {
    if (!map) {
      return;
    }
    const maps = googleMapsApi();
    const bounds = new maps.LatLngBounds();
    bounds.extend(new maps.LatLng(SITE_INFO.geo.latitude, SITE_INFO.geo.longitude));
    for (const order of orders) {
      bounds.extend(new maps.LatLng(order.lat, order.lng));
    }
    map.fitBounds(bounds, 80);
  }, [map, orders]);

  const overlays = [...sortCrmBoardOrders(orders)].reverse();

  return (
    <div className="relative h-full w-full">
      <div ref={containerRef} className="h-full w-full" />
      {map ? (
        <>
          <CrmMapBakeryOverlay map={map} />
          {overlays.map((order) => (
            <CrmMapOverlay key={order.id} map={map} order={order} />
          ))}
        </>
      ) : null}
    </div>
  );
}
