const GOOGLE_MAPS_SCRIPT_ID = "google-maps-js";

export type GoogleLatLngLiteral = { lat: number; lng: number };

export type GoogleLatLng = {
  lat: () => number;
  lng: () => number;
};

export type GoogleLatLngBounds = {
  extend: (latLng: GoogleLatLng) => void;
};

export type GoogleMapInstance = {
  fitBounds: (bounds: GoogleLatLngBounds, padding: number) => void;
};

type GoogleMapPanes = {
  overlayMouseTarget: HTMLElement;
};

type GoogleMapProjection = {
  fromLatLngToDivPixel: (latLng: GoogleLatLng) => { x: number; y: number } | null;
};

export type GoogleOverlayView = {
  setMap: (map: GoogleMapInstance | null) => void;
  getPanes: () => GoogleMapPanes | null;
  getProjection: () => GoogleMapProjection;
  onAdd: () => void;
  draw: () => void;
  onRemove: () => void;
};

export type GoogleMapsNamespace = {
  Map: new (
    el: HTMLElement,
    opts: {
      center: GoogleLatLngLiteral;
      zoom: number;
      clickableIcons: boolean;
      mapTypeControl: boolean;
      streetViewControl: boolean;
      fullscreenControl: boolean;
      gestureHandling: string;
      maxZoom: number;
    },
  ) => GoogleMapInstance;
  OverlayView: new () => GoogleOverlayView;
  LatLng: new (lat: number, lng: number) => GoogleLatLng;
  LatLngBounds: new () => GoogleLatLngBounds;
};

function windowGoogle(): { maps: GoogleMapsNamespace } | undefined {
  return (window as unknown as { google?: { maps: GoogleMapsNamespace } }).google;
}

export function googleMapsApi(): GoogleMapsNamespace {
  const google = windowGoogle();
  if (!google) {
    throw new Error("Google Maps is not loaded");
  }
  return google.maps;
}

export function loadGoogleMaps(apiKey: string): Promise<GoogleMapsNamespace> {
  if (windowGoogle()?.maps) {
    return Promise.resolve(googleMapsApi());
  }
  const existing = document.getElementById(GOOGLE_MAPS_SCRIPT_ID);
  if (existing) {
    return new Promise((resolve) => {
      existing.addEventListener("load", () => resolve(googleMapsApi()));
    });
  }
  return new Promise((resolve) => {
    const script = document.createElement("script");
    script.id = GOOGLE_MAPS_SCRIPT_ID;
    script.src = `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(apiKey)}`;
    script.async = true;
    script.onload = () => resolve(googleMapsApi());
    script.onerror = () => {
      throw new Error("Failed to load Google Maps");
    };
    document.head.appendChild(script);
  });
}

export function attachHtmlOverlay(
  maps: GoogleMapsNamespace,
  map: GoogleMapInstance,
  position: GoogleLatLngLiteral,
  container: HTMLDivElement,
): GoogleOverlayView {
  const overlay = new maps.OverlayView();
  overlay.onAdd = () => {
    const panes = overlay.getPanes();
    if (!panes) {
      throw new Error("Google Maps overlay panes are missing");
    }
    panes.overlayMouseTarget.appendChild(container);
  };
  overlay.draw = () => {
    const point = overlay.getProjection().fromLatLngToDivPixel(
      new maps.LatLng(position.lat, position.lng),
    );
    if (!point) {
      return;
    }
    container.style.left = `${point.x}px`;
    container.style.top = `${point.y}px`;
  };
  overlay.onRemove = () => {
    container.remove();
  };
  overlay.setMap(map);
  return overlay;
}
