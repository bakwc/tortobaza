export const MAP_COORDS = "41.621184,41.614267";

export const MAP_LINK = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(
  MAP_COORDS,
)}`;

export const MAP_EMBED = `https://maps.google.com/maps?q=${encodeURIComponent(
  MAP_COORDS,
)}&hl=en&z=15&output=embed`;
