/**
 * Minimal OKLCH <-> sRGB conversions for live editing in the UI.
 * Ported from palette_generator/color/spaces.py (Björn Ottosson's OKLab constants);
 * the server remains the source of truth for scoring/roles — this exists so slider
 * dragging can preview colors without a network round-trip.
 */

export interface Oklch {
  l: number;
  c: number;
  h: number; // degrees
}

type Rgb = [number, number, number];

const srgbToLinear = (v: number): number =>
  v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;

const linearToSrgb = (v: number): number =>
  v <= 0.0031308 ? 12.92 * v : 1.055 * v ** (1 / 2.4) - 0.055;

export function hexToRgb(hex: string): Rgb {
  const h = hex.replace("#", "");
  const n = parseInt(h.length === 3 ? [...h].map((c) => c + c).join("") : h, 16);
  return [((n >> 16) & 255) / 255, ((n >> 8) & 255) / 255, (n & 255) / 255];
}

export function rgbToHex([r, g, b]: Rgb): string {
  const q = (v: number) =>
    Math.round(Math.min(1, Math.max(0, v)) * 255)
      .toString(16)
      .padStart(2, "0");
  return `#${q(r)}${q(g)}${q(b)}`;
}

export function rgbToOklch(rgb: Rgb): Oklch {
  const [r, g, b] = rgb.map(srgbToLinear);
  const lp = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b;
  const mp = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b;
  const sp = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b;
  const l_ = Math.cbrt(lp);
  const m_ = Math.cbrt(mp);
  const s_ = Math.cbrt(sp);
  const L = 0.2104542553 * l_ + 0.793617785 * m_ - 0.0040720468 * s_;
  const a = 1.9779984951 * l_ - 2.428592205 * m_ + 0.4505937099 * s_;
  const bb = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.808675766 * s_;
  const c = Math.hypot(a, bb);
  const h = ((Math.atan2(bb, a) * 180) / Math.PI + 360) % 360;
  return { l: L, c, h };
}

function oklchToRgbRaw({ l, c, h }: Oklch): Rgb {
  const rad = (h * Math.PI) / 180;
  const a = c * Math.cos(rad);
  const b = c * Math.sin(rad);
  const l_ = l + 0.3963377774 * a + 0.2158037573 * b;
  const m_ = l - 0.1055613458 * a - 0.0638541728 * b;
  const s_ = l - 0.0894841775 * a - 1.291485548 * b;
  const lc = l_ ** 3;
  const mc = m_ ** 3;
  const sc = s_ ** 3;
  return [
    linearToSrgb(4.0767416621 * lc - 3.3077115913 * mc + 0.2309699292 * sc),
    linearToSrgb(-1.2684380046 * lc + 2.6097574011 * mc - 0.3413193965 * sc),
    linearToSrgb(-0.0041960863 * lc - 0.7034186147 * mc + 1.707614701 * sc),
  ];
}

export function inGamut(rgb: Rgb, eps = 1e-4): boolean {
  return rgb.every((v) => v >= -eps && v <= 1 + eps);
}

/** True if this OKLCH color needs chroma reduction to fit sRGB. */
export function isClamped(color: Oklch): boolean {
  return !inGamut(oklchToRgbRaw(color));
}

/** Largest in-gamut chroma at this L/H (binary search, matches the Python core). */
export function clampToGamut(color: Oklch): Oklch {
  const { l, h } = color;
  if (l <= 0) return { l: 0, c: 0, h };
  if (l >= 1) return { l: 1, c: 0, h };
  if (inGamut(oklchToRgbRaw(color))) return color;
  let lo = 0;
  let hi = color.c;
  for (let i = 0; i < 24; i++) {
    const mid = (lo + hi) / 2;
    if (inGamut(oklchToRgbRaw({ l, c: mid, h }))) lo = mid;
    else hi = mid;
  }
  return { l, c: lo, h };
}

export function oklchToHex(color: Oklch): string {
  return rgbToHex(oklchToRgbRaw(clampToGamut(color)));
}

export function hexToOklch(hex: string): Oklch {
  return rgbToOklch(hexToRgb(hex));
}
