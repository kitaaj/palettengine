/**
 * Real-time palette sampling for Ambient Mode.
 *
 * Runs entirely in the browser on a tiny (e.g. 32x18) downscaled video frame, so it is
 * cheap enough for ~10 fps live updates. k-means is **warm-started from the previous
 * frame's centers**, which both (a) converges in 2-3 iterations because consecutive
 * frames barely change, and (b) makes the palette glide smoothly instead of flickering.
 *
 * Colors are clustered in OKLab so the live palette is perceptually sensible — the same
 * space the rest of Palettengine uses.
 */

export type Lab = [number, number, number];

const srgbToLinear = (v: number): number =>
  v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
const linearToSrgb = (v: number): number =>
  v <= 0.0031308 ? 12.92 * v : 1.055 * v ** (1 / 2.4) - 0.055;

function rgb8ToLab(r: number, g: number, b: number): Lab {
  const lr = srgbToLinear(r / 255);
  const lg = srgbToLinear(g / 255);
  const lb = srgbToLinear(b / 255);
  const l_ = Math.cbrt(0.4122214708 * lr + 0.5363325363 * lg + 0.0514459929 * lb);
  const m_ = Math.cbrt(0.2119034982 * lr + 0.6806995451 * lg + 0.1073969566 * lb);
  const s_ = Math.cbrt(0.0883024619 * lr + 0.2817188376 * lg + 0.6299787005 * lb);
  return [
    0.2104542553 * l_ + 0.793617785 * m_ - 0.0040720468 * s_,
    1.9779984951 * l_ - 2.428592205 * m_ + 0.4505937099 * s_,
    0.0259040371 * l_ + 0.7827717662 * m_ - 0.808675766 * s_,
  ];
}

function clamp01(v: number): number {
  return v < 0 ? 0 : v > 1 ? 1 : v;
}

export function labToHex([L, a, b]: Lab): string {
  const l_ = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3;
  const m_ = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3;
  const s_ = (L - 0.0894841775 * a - 1.291485548 * b) ** 3;
  const r = clamp01(linearToSrgb(4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_));
  const g = clamp01(linearToSrgb(-1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_));
  const bl = clamp01(linearToSrgb(-0.0041960863 * l_ - 0.7034186147 * m_ + 1.707614701 * s_));
  const q = (v: number) =>
    Math.round(v * 255)
      .toString(16)
      .padStart(2, "0");
  return `#${q(r)}${q(g)}${q(bl)}`;
}

function dist2(a: Lab, b: Lab): number {
  const dl = a[0] - b[0];
  const da = a[1] - b[1];
  const db = a[2] - b[2];
  return dl * dl + da * da + db * db;
}

/** Spread initial centers across the lightness range of the sample. */
function initCenters(labs: Lab[], k: number): Lab[] {
  const order = labs.map((_, i) => i).sort((i, j) => labs[i][0] - labs[j][0]);
  const centers: Lab[] = [];
  for (let j = 0; j < k; j++) {
    const idx = order[Math.min(order.length - 1, Math.floor(((j + 0.5) / k) * order.length))];
    centers.push([...labs[idx]]);
  }
  return centers;
}

export interface LiveSample {
  centers: Lab[];
  hexes: string[];
}

/**
 * Cluster an RGBA pixel buffer into ``k`` OKLab centers, sorted dark→light.
 * Pass the previous call's ``centers`` as ``prev`` to warm-start (smooth + fast).
 */
export function samplePalette(
  rgba: Uint8ClampedArray,
  k = 5,
  prev?: Lab[],
  iterations = 3,
): LiveSample {
  const n = rgba.length >> 2;
  const labs: Lab[] = new Array(n);
  for (let i = 0; i < n; i++) {
    const o = i << 2;
    labs[i] = rgb8ToLab(rgba[o], rgba[o + 1], rgba[o + 2]);
  }

  let centers: Lab[] = prev && prev.length === k ? prev.map((c) => [...c] as Lab) : initCenters(labs, k);

  for (let it = 0; it < iterations; it++) {
    const sums: Lab[] = Array.from({ length: k }, () => [0, 0, 0] as Lab);
    const counts = new Array(k).fill(0);
    for (let i = 0; i < n; i++) {
      const p = labs[i];
      let best = 0;
      let bestD = Infinity;
      for (let j = 0; j < k; j++) {
        const d = dist2(p, centers[j]);
        if (d < bestD) {
          bestD = d;
          best = j;
        }
      }
      sums[best][0] += p[0];
      sums[best][1] += p[1];
      sums[best][2] += p[2];
      counts[best]++;
    }
    for (let j = 0; j < k; j++) {
      if (counts[j] > 0) {
        centers[j] = [sums[j][0] / counts[j], sums[j][1] / counts[j], sums[j][2] / counts[j]];
      }
    }
  }

  centers = centers.sort((a, b) => a[0] - b[0]);
  return { centers, hexes: centers.map(labToHex) };
}
