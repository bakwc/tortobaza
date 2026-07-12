export type TextDecoration = {
  id: string;
  kind: "text";
  text: string;
  x: number;
  y: number;
  scale: number;
};

export type ImageDecoration = {
  id: string;
  kind: "image";
  src: string;
  x: number;
  y: number;
  scale: number;
};

export type Decoration = TextDecoration | ImageDecoration;

export const CAKE_RADIUS = 1.2;
export const CAKE_HEIGHT = 0.75;
export const BOARD_RADIUS = 1.55;
export const BOARD_HEIGHT = 0.06;
export const DECORATION_Y = CAKE_HEIGHT + 0.015;

export function clampToCake(x: number, y: number, margin = 0.15): [number, number] {
  const maxR = CAKE_RADIUS - margin;
  const len = Math.hypot(x, y);
  if (len <= maxR) {
    return [x, y];
  }
  const s = maxR / len;
  return [x * s, y * s];
}
