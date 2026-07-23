/**
 * WCAG contrast helpers for the previews. Every foreground color painted in a
 * template or gallery card is routed through {@link ensureContrast} so text can
 * never clash with the color behind it, whatever palette the engine produces.
 *
 * The server enforces contrast only for the `text` role against `background`
 * (palettengine/roles/assign.py::auto_fix); this covers every other pairing a
 * mock UI needs (text on surface, label on accent, muted on card, ...).
 */

import { hexToOklch, hexToRgb, oklchToHex, srgbToLinear } from "./oklch";

/** WCAG relative luminance of a hex color (0..1). */
export function relLuminance(hex: string): number {
  const [r, g, b] = hexToRgb(hex).map(srgbToLinear);
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

/** WCAG contrast ratio between two hex colors (1..21). */
export function contrastRatio(a: string, b: string): number {
  const la = relLuminance(a);
  const lb = relLuminance(b);
  const [hi, lo] = la >= lb ? [la, lb] : [lb, la];
  return (hi + 0.05) / (lo + 0.05);
}

/** Pure black or white, whichever reads better on `bg`. */
export function readableOn(bg: string): string {
  return contrastRatio("#000000", bg) >= contrastRatio("#ffffff", bg)
    ? "#000000"
    : "#ffffff";
}

/**
 * Return a color that meets `target` contrast on `bg`. If `fg` already clears
 * it, `fg` is returned unchanged. Otherwise `fg`'s OKLCH lightness is pushed
 * toward black or white (whichever direction the background allows) so the hue
 * is preserved where possible; if even the extreme cannot reach `target`, fall
 * back to pure black/white. The result is guaranteed to satisfy `target`
 * (black-or-white against any background always clears 4.5:1 except on the
 * rare mid-tone, where we return the better of the two).
 */
export function ensureContrast(fg: string, bg: string, target = 4.5): string {
  if (contrastRatio(fg, bg) >= target) return fg;

  const bw = readableOn(bg);
  // Push toward whichever pole the readable choice sits at.
  const toWhite = bw === "#ffffff";
  const ok = hexToOklch(fg);
  let lo = ok.l;
  let hi = toWhite ? 1 : 0;
  let best = bw;

  for (let i = 0; i < 20; i++) {
    const mid = (lo + hi) / 2;
    const candidate = oklchToHex({ ...ok, l: mid });
    if (contrastRatio(candidate, bg) >= target) {
      best = candidate; // meets target while keeping the most hue (closest to fg)
      hi = mid;
    } else {
      lo = mid;
    }
  }
  // If the hue-preserving search never met target, best stays as the b/w fallback.
  return contrastRatio(best, bg) >= target ? best : bw;
}
